"""
RNG Validation Battery (report Annex A)

Implements 5 statistical tests for pseudo-random number generators,
applied to two generators:
  1. The custom LCG (m=2^31, a=1103515245, c=12345) — the generator actually
     used by util.exponential() / util.lognormal() in the main simulation
     (drawn here from the same util.LCG class).
  2. Python's random.random() (Mersenne Twister) — kept as a reference
     comparison only; the simulation no longer uses it.

Tests:
  A. Frequency test (Kolmogorov-Smirnov vs U(0,1))
  B. Gap test (chi-square on gap lengths between hits in [0, 0.5))
  C. Order test (chi-square on permutation patterns of d=4 consecutive draws)
  D. Runs test (up/down runs, normal approximation)
  E. Serial/autocorrelation test (lag-1 correlation, normal approximation)
"""
import math
import random
import numpy as np
from scipy import stats
from itertools import permutations


# ============================================================
# Generators
# ============================================================

def generate_lcg(n, seed=42):
    """Custom LCG stream, drawn from the same util.LCG used by the simulation.

    X(n+1) = (a*X(n) + c) mod m, normalised to [0,1)
    with m=2^31, a=1103515245, c=12345.
    """
    from util import LCG
    rng = LCG(seed=seed)
    values = np.empty(n)
    for i in range(n):
        values[i] = rng.random()
    return values


def generate_mt(n, seed=42):
    """Python's Mersenne Twister via random.random()."""
    rng = random.Random(seed)
    return np.array([rng.random() for _ in range(n)])


# ============================================================
# Test A — Frequency test (Kolmogorov-Smirnov uniformity)
# ============================================================

def frequency_test(x):
    """KS test against U(0,1). H0: x ~ Uniform(0,1)."""
    stat, pval = stats.kstest(x, 'uniform')
    return {"statistic": stat, "p_value": pval}


# ============================================================
# Test B — Gap test
# Gaps between successive values that fall in [0, 0.5).
# Under H0, gap lengths ~ Geometric(p=0.5); compare observed vs
# expected gap-length distribution via chi-square.
# ============================================================

def gap_test(x, lower=0.0, upper=0.5, max_gap=15):
    p = upper - lower
    in_range = (x >= lower) & (x < upper)
    idx = np.where(in_range)[0]
    if len(idx) < 2:
        return {"statistic": None, "p_value": None, "note": "not enough hits"}

    gaps = np.diff(idx) - 1  # number of misses between consecutive hits
    gaps = np.clip(gaps, 0, max_gap)  # bucket tail into max_gap

    observed = np.bincount(gaps, minlength=max_gap + 1).astype(float)
    n_gaps = observed.sum()

    # Expected geometric probabilities P(gap=k) = p*(1-p)^k, last bucket = tail
    k = np.arange(max_gap + 1)
    expected_p = p * (1 - p) ** k
    expected_p[-1] = (1 - p) ** max_gap  # P(gap >= max_gap)
    expected = expected_p * n_gaps

    # Merge bins with expected count < 5 to keep chi-square valid
    obs, exp = [], []
    run_o, run_e = 0.0, 0.0
    for o, e in zip(observed, expected):
        run_o += o
        run_e += e
        if run_e >= 5:
            obs.append(run_o)
            exp.append(run_e)
            run_o, run_e = 0.0, 0.0
    if run_e > 0:
        if obs:
            obs[-1] += run_o
            exp[-1] += run_e
        else:
            obs.append(run_o)
            exp.append(run_e)

    chi2 = sum((o - e) ** 2 / e for o, e in zip(obs, exp))
    dof = len(obs) - 1
    pval = 1 - stats.chi2.cdf(chi2, dof) if dof > 0 else None
    return {"statistic": chi2, "p_value": pval, "dof": dof, "n_gaps": int(n_gaps)}


# ============================================================
# Test C — Order test
# Take non-overlapping groups of d=4 consecutive draws, rank them
# (1..d! possible orderings). Under H0 each ordering is equally
# likely (1/d!). Chi-square goodness of fit.
# ============================================================

def order_test(x, d=4):
    n_groups = len(x) // d
    x = x[:n_groups * d].reshape(n_groups, d)

    perms = list(permutations(range(d)))
    perm_index = {p: i for i, p in enumerate(perms)}

    counts = np.zeros(len(perms))
    for row in x:
        order = tuple(np.argsort(row))
        counts[perm_index[order]] += 1

    expected = n_groups / len(perms)
    chi2 = np.sum((counts - expected) ** 2 / expected)
    dof = len(perms) - 1
    pval = 1 - stats.chi2.cdf(chi2, dof)
    return {"statistic": chi2, "p_value": pval, "dof": dof, "n_groups": n_groups}


# ============================================================
# Test D — Runs test (up/down)
# Counts runs of consecutive increases/decreases; compares to the
# expected number of runs under independence (normal approximation).
# ============================================================

def runs_test(x):
    n = len(x)
    diffs = np.diff(x)
    signs = np.sign(diffs)
    signs = signs[signs != 0]  # drop ties
    n_eff = len(signs) + 1

    runs = 1
    for i in range(1, len(signs)):
        if signs[i] != signs[i - 1]:
            runs += 1

    # Expected runs and variance (Law & Kelton up/down runs test)
    mu = (2 * n_eff - 1) / 3
    var = (16 * n_eff - 29) / 90
    z = (runs - mu) / math.sqrt(var)
    pval = 2 * (1 - stats.norm.cdf(abs(z)))
    return {"statistic": z, "p_value": pval, "runs": runs, "expected": mu}


# ============================================================
# Test E — Serial / autocorrelation test (lag-1)
# Pearson correlation between x_i and x_{i+1}; under H0 this is 0.
# Normal approximation for significance.
# ============================================================

def serial_test(x):
    n = len(x)
    x0 = x[:-1]
    x1 = x[1:]
    r = np.corrcoef(x0, x1)[0, 1]
    z = r * math.sqrt(n - 1)
    pval = 2 * (1 - stats.norm.cdf(abs(z)))
    return {"statistic": r, "p_value": pval, "z": z}


# ============================================================
# Runner
# ============================================================

def run_battery(x, name):
    print(f"\n{'='*60}")
    print(f"  {name}  (n={len(x)})")
    print(f"{'='*60}")

    results = {}
    results["A_frequency"] = frequency_test(x)
    results["B_gap"] = gap_test(x)
    results["C_order"] = order_test(x, d=4)
    results["D_runs"] = runs_test(x)
    results["E_serial"] = serial_test(x)

    for key, r in results.items():
        pval = r["p_value"]
        verdict = "RANDOM" if (pval is not None and pval >= 0.05) else "NOT RANDOM"
        stat = r["statistic"]
        print(f"  {key:<14} stat={stat:>10.5f}   p={pval:>8.5f}   -> {verdict}")
    return results


if __name__ == "__main__":
    N = 10000

    lcg = generate_lcg(N, seed=42)
    mt = generate_mt(N, seed=42)

    print("LCG: m=2^31, a=1103515245, c=12345, seed=42 — the generator used by")
    print("     the main simulation's util.exponential() / util.lognormal()")
    print("MT:  Python random.Random(42).random() — reference comparison only")

    lcg_results = run_battery(lcg, "Custom LCG (simulation generator)")
    mt_results = run_battery(mt, "Mersenne Twister (reference only)")

    print(f"\n{'='*60}")
    print("  SUMMARY")
    print(f"{'='*60}")
    print(f"  {'Test':<14}{'LCG p-value':>14}{'MT p-value':>14}")
    for key in lcg_results:
        lp = lcg_results[key]["p_value"]
        mp = mt_results[key]["p_value"]
        print(f"  {key:<14}{lp:>14.5f}{mp:>14.5f}")
