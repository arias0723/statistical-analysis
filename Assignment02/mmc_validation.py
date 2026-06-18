import math
from simulator import Simulator
from queue_model import QueueModel
from util import LCG, exponential

def erlang_c_wq(lam, mu, c):
    """Theoretical mean wait in queue for M/M/c (Erlang-C formula).
    lam = arrival rate, mu = per-server service rate, c = servers.
    Returns W_q in same time units as 1/mu.
    """
    rho = lam / (c * mu)
    if rho >= 1:
        return None
    a = lam / mu  # offered load (Erlangs)
    # Erlang-C probability of waiting
    sum_terms = sum((a**n) / math.factorial(n) for n in range(c))
    last_term = (a**c) / (math.factorial(c) * (1 - rho))
    p_wait = last_term / (sum_terms + last_term)
    wq = p_wait / (c * mu - lam)
    return {"rho": rho, "p_wait": p_wait, "wq": wq}

def run_mmc(lam, mu, c, until=80000.0, seed=42):
    sim = Simulator()
    rng_arr = LCG(seed=seed)
    rng_svc = LCG(seed=seed + 1)
    q = QueueModel(sim=sim, name=f"M/M/{c}",
                   arrival_dist=exponential(lam, rng_arr),
                   service_dist=exponential(mu, rng_svc),
                   servers=c, capacity=float('inf'), discipline='FIFO')
    q.start_generator()
    sim.run(until=until)
    return q

# Test case: M/M/4, lambda=3.0, mu=1.0 per server -> rho=0.75
# Chosen to mirror the M/M/1 rho=0.75 but exercise multi-server logic
lam, mu, c = 3.0, 1.0, 4
print("M/M/c VALIDATION (Erlang-C)")
print("=" * 60)
print(f"Parameters: lambda={lam}, mu={mu}/server, c={c}, rho={lam/(c*mu):.3f}")
print()

theory = erlang_c_wq(lam, mu, c)
q = run_mmc(lam, mu, c)

sim_wq = q.avg_wait_time()
sim_rho = q.utilization()
sim_lq = q.avg_queue_length()

print(f"  {'Metric':<14}{'Theory':>12}{'Simulated':>12}{'Error':>10}")
print("  " + "-" * 46)
print(f"  {'W_q':<14}{theory['wq']:>12.4f}{sim_wq:>12.4f}{abs(sim_wq-theory['wq'])/theory['wq']*100:>9.2f}%")
print(f"  {'rho':<14}{theory['rho']:>12.4f}{sim_rho:>12.4f}{abs(sim_rho-theory['rho'])/theory['rho']*100:>9.2f}%")
# L_q theory via Little: Lq = lambda * Wq
lq_theory = lam * theory['wq']
print(f"  {'L_q':<14}{lq_theory:>12.4f}{sim_lq:>12.4f}{abs(sim_lq-lq_theory)/lq_theory*100:>9.2f}%")
print(f"  {'P(wait)':<14}{theory['p_wait']:>12.4f}{'—':>12}{'—':>10}")
print()
print(f"  Little's Law: L_q = lambda*W_q -> {sim_lq:.4f} vs {lam*sim_wq:.4f}")
