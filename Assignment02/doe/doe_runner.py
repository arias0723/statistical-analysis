"""
doe_runner.py  -- 2^3 factorial DOE for the HPC batch-queue model.

Rebuilt to address two issues in the original single-replication runner:

  1. RNG-STREAM COUPLING.  The original used one shared random stream, so
     changing one factor (e.g. c_Standard) reordered the global event
     sequence and perturbed partitions it should not have touched -- e.g.
     P_b_Short and W_q_Long changed between cells that differ only in
     c_Standard.  Here each partition draws service times from its OWN
     stream, and arrivals/routing have their own streams, all seeded as a
     function of the replication index ONLY (not the cell).  This is
     common random numbers (CRN): cells that leave a partition's load
     unchanged produce bit-identical results for that partition, so its
     metrics cannot drift, and CRN reduces the variance of factor
     comparisons.

  2. SINGLE REPLICATION.  The original ran n=1 per cell, so effect
     estimates carried no error bars and could not be separated from
     noise.  Here each cell is replicated R times (CRN-paired across
     cells), cell responses are reported as mean +/- 95% CI, and each
     2^3 effect is reported with a standard error and 95% CI from the
     pooled within-cell variance (Montgomery, DOE).

Service: log-normal, mean=2h, CV=1.5 (SD_01), per partition.
Run length: 500h warm-up + 4000h collection (matches Section 6.3 / 9.3).
"""

import heapq
import math
import os
import sys
from dataclasses import dataclass, field
from itertools import product
from statistics import mean, variance

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from util import LCG  # custom RNG shared with the main simulation

MU = 0.5  # service rate per server (1 / 2h mean)

# log-normal(mean=2, CV=1.5) underlying-normal params
_SIGMA = math.sqrt(math.log(1 + 1.5 ** 2))
_MU_LOG = math.log(2.0) - _SIGMA ** 2 / 2


def lognormal(rng):
    # Box-Muller standard normal from two custom-LCG uniforms.
    u1, u2 = rng.random(), rng.random()
    z = math.sqrt(-2.0 * math.log(1.0 - u1)) * math.cos(2.0 * math.pi * u2)
    return math.exp(_MU_LOG + _SIGMA * z)


# ----------------------------------------------------------------------
@dataclass
class Partition:
    name: str
    c: int
    N: int
    rng: LCG                      # OWN service stream (custom LCG)
    in_service: int = 0
    queue: list = field(default_factory=list)
    wait_sum: float = 0.0
    served: int = 0
    arrivals: int = 0
    blocked: int = 0
    busy_area: float = 0.0
    last_t: float = 0.0

    def in_system(self):
        return self.in_service + len(self.queue)

    def advance(self, t):
        self.busy_area += self.in_service * (t - self.last_t)
        self.last_t = t

    def reset_stats(self, t):
        self.advance(t)
        self.wait_sum = self.busy_area = 0.0
        self.served = self.arrivals = self.blocked = 0
        self.last_t = t


class System:
    def __init__(self, lam, weights, parts, arr_rng, route_rng):
        self.lam = lam
        self.weights = weights
        self.parts = parts
        self.arr_rng = arr_rng
        self.route_rng = route_rng
        self.t = 0.0
        self.collecting = False
        self.heap = []
        self.seq = 0
        self._sched_arrival()

    def _push(self, time, kind, idx):
        heapq.heappush(self.heap, (time, self.seq, kind, idx))
        self.seq += 1

    def _sched_arrival(self):
        # Inverse-transform exponential inter-arrival from the custom LCG.
        u = self.arr_rng.random()
        self._push(self.t + (-math.log(1.0 - u) / self.lam), "arr", -1)

    def _pick(self):
        r = self.route_rng.random()
        acc = 0.0
        for i, w in enumerate(self.weights):
            acc += w
            if r < acc:
                return i
        return len(self.weights) - 1

    def _start(self, p, arr_t):
        if self.collecting:
            p.wait_sum += self.t - arr_t
            p.served += 1
        p.advance(self.t)
        p.in_service += 1
        self._push(self.t + lognormal(p.rng), "dep", self.parts.index(p))

    def run(self, t_end):
        while self.heap and self.heap[0][0] <= t_end:
            time, _, kind, idx = heapq.heappop(self.heap)
            self.t = time
            if kind == "arr":
                p = self.parts[self._pick()]
                if self.collecting:
                    p.arrivals += 1
                if p.in_system() >= p.N:
                    if self.collecting:
                        p.blocked += 1
                elif p.in_service < p.c:
                    self._start(p, self.t)
                else:
                    p.queue.append(self.t)
                self._sched_arrival()
            else:
                p = self.parts[idx]
                p.advance(self.t)
                p.in_service -= 1
                if p.queue:
                    self._start(p, p.queue.pop(0))
        self.t = t_end
        for p in self.parts:
            p.advance(t_end)

    def begin_collection(self, t):
        self.collecting = True
        for p in self.parts:
            p.reset_stats(t)


def run_cell(lam, w_std, c_std, rep, warmup=500.0, collect=4000.0):
    """One replication of one design cell. Seeds depend on rep ONLY -> CRN."""
    # remaining weight split 1:3 between Short and Long (matches baseline 0.05:0.15)
    rem = 1.0 - w_std
    weights = [rem * 0.25, w_std, rem * 0.75]   # [Short, Standard, Long]
    parts = [
        Partition("Short",    16,  50, LCG(3000 + rep)),
        Partition("Standard", c_std, 200, LCG(4000 + rep)),
        Partition("Long",     32, 100, LCG(5000 + rep)),
    ]
    sysm = System(lam, weights, parts,
                  LCG(1000 + rep), LCG(2000 + rep))
    sysm.run(warmup)
    sysm.begin_collection(warmup)
    sysm.run(warmup + collect)

    out = {}
    for p in parts:
        out[f"wq_{p.name}"] = p.wait_sum / p.served if p.served else 0.0
        out[f"rho_{p.name}"] = p.busy_area / (p.c * collect)
        out[f"pb_{p.name}"] = p.blocked / p.arrivals if p.arrivals else 0.0
    tot_block = sum(p.blocked for p in parts)
    tot_arr = sum(p.arrivals for p in parts)
    out["pb_total"] = tot_block / tot_arr if tot_arr else 0.0
    return out


# ----------------------------------------------------------------------
# 2^3 design
LEVELS = {"lam": (30, 60), "w_std": (0.65, 0.80), "c_std": (64, 80)}
RESPONSES = ["wq_Standard", "pb_Standard", "pb_total",
             "wq_Short", "pb_Short", "wq_Long", "pb_Long"]


def t_crit(df, p=0.975):
    # small-table lookup, falls back to normal for large df
    table = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447,
             7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228, 12: 2.179, 15: 2.131,
             16: 2.120, 20: 2.086, 24: 2.064, 30: 2.042, 32: 2.037,
             40: 2.021, 56: 2.003, 64: 1.998, 72: 1.993, 80: 1.990,
             120: 1.980}
    if df in table:
        return table[df]
    keys = sorted(table)
    for k in keys:
        if df <= k:
            return table[k]
    return 1.96


def run_doe(R=10):
    cells = list(product(LEVELS["lam"], LEVELS["w_std"], LEVELS["c_std"]))
    # data[cell] = list of per-rep response dicts
    data = {cell: [run_cell(cell[0], cell[1], cell[2], rep)
                   for rep in range(1, R + 1)] for cell in cells}

    # ---- per-cell summary ----
    print(f"\n{'='*100}\n2^3 DOE cell results  (R={R} replications/cell, "
          f"warm-up 500h + collect 4000h, CRN across cells)\n{'='*100}")
    hdr = (f"{'run':>3} {'lam':>4} {'w_St':>5} {'c_St':>5} {'off_rhoSt':>9} "
           f"{'Wq_Std':>16} {'Pb_Std':>16} {'Pb_Short':>16} {'Wq_Long':>16}")
    print(hdr)
    cell_means = {}
    cell_vars = {}
    for i, cell in enumerate(cells, 1):
        lam, w, c = cell
        reps = data[cell]
        cm = {r: mean(d[r] for d in reps) for r in reps[0]}
        cv = {r: (variance(d[r] for d in reps) if R > 1 else 0.0) for r in reps[0]}
        cell_means[cell] = cm
        cell_vars[cell] = cv
        off = lam * w / (c * MU)
        tc = t_crit(R - 1)

        def ci(r):
            return tc * math.sqrt(cv[r] / R) if R > 1 else 0.0
        print(f"{i:>3} {lam:>4} {w:>5.2f} {c:>5} {off:>9.3f} "
              f"{cm['wq_Standard']:>7.4f}±{ci('wq_Standard'):<7.4f} "
              f"{cm['pb_Standard']:>7.4f}±{ci('pb_Standard'):<7.4f} "
              f"{cm['pb_Short']:>7.4f}±{ci('pb_Short'):<7.4f} "
              f"{cm['wq_Long']:>7.4f}±{ci('wq_Long'):<7.4f}")

    # ---- effects with error bars ----
    # pooled within-cell variance, df = 2^3 (R-1)
    df_pooled = len(cells) * (R - 1)
    tc = t_crit(df_pooled)
    signs = {  # +/- level coding for each factor at each cell
        cell: {"A": 1 if cell[0] == LEVELS["lam"][1] else -1,
               "B": 1 if cell[1] == LEVELS["w_std"][1] else -1,
               "C": 1 if cell[2] == LEVELS["c_std"][1] else -1}
        for cell in cells}
    terms = ["A", "B", "C", "AB", "AC", "BC", "ABC"]

    def sign_of(term, cell):
        s = 1
        for ch in term:
            s *= signs[cell][ch]
        return s

    print(f"\n{'='*100}\nFactor effects with 95% CI "
          f"(pooled s^2, df={df_pooled}; effect significant if CI excludes 0)"
          f"\n  A = lambda (30->60)   B = w_Standard (0.65->0.80)   "
          f"C = c_Standard (64->80)\n{'='*100}")
    for resp in ["pb_Standard", "wq_Standard", "pb_total"]:
        s2 = mean(cell_vars[c][resp] for c in cells) if R > 1 else 0.0
        se = math.sqrt(s2 / (R * 2 ** (3 - 2))) if R > 1 else 0.0  # /(R*2)
        half = tc * se
        print(f"\n  {resp}:   (effect SE = {se:.4f}, 95% CI half-width = "
              f"±{half:.4f})")
        for term in terms:
            eff = mean(sign_of(term, c) * cell_means[c][resp] for c in cells) * 2
            sig = "  *" if abs(eff) > half else ""
            print(f"     {term:<4} {eff:>+9.4f}{sig}")
    return data, cell_means


if __name__ == "__main__":
    import sys
    R = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    run_doe(R)
