from util import *
from simulator import Simulator
from queue_model import QueueModel, Router
import random


def validate_mm1(rho: float) -> dict:
    """Compute theoretical M/M/1 performance metrics.

    Args:
        rho: utilization = λ / μ (must be < 1)

    Returns:
        dict with theoretical values: avg_wait_in_queue, avg_queue_length, etc.
    """
    if rho >= 1:
        return {"error": "M/M/1 unstable (ρ >= 1)"}

    # M/M/1 formulas (waits in units of 1/μ)
    avg_wait_in_queue = rho / (1 - rho)
    avg_queue_length = rho**2 / (1 - rho)
    avg_wait_in_system = 1 / (1 - rho)

    return {
        "rho": rho,
        "avg_wait_in_queue": avg_wait_in_queue,
        "avg_queue_length": avg_queue_length,
        "avg_wait_in_system": avg_wait_in_system,
    }


def print_queue_stats(queue: QueueModel):
    """Pretty-print statistics for a single queue/partition."""
    print(f"  Partition: {queue.name}  (c={queue.servers}, N={queue.capacity})")
    print(f"    Processed:            {queue.entities_processed}")
    print(f"    Blocked (full):       {queue.entities_dropped}")
    print(f"    Promoted out (aging): {queue.entities_promoted}")
    print(f"    Throughput (jobs/h):  {queue.throughput():.4f}")
    print(f"    Avg wait W_q (h):     {queue.avg_wait_time():.4f}")
    print(f"    Avg queue length L_q: {queue.avg_queue_length():.4f}")
    print(f"    Server utilisation ρ: {queue.utilization():.4f}")
    print(f"    Blocking prob. P_b:   {queue.blocking_probability():.4f}")


def run_hpc_cluster(arrival_lambda: float = 45.0,
                    weights=(0.05, 0.80, 0.15),
                    service_mean_h: float = 2.0,
                    service_cv: float = 1.5,
                    aging: bool = True,
                    until: float = 4000.0,
                    seed: int = 42):
    """Run the 3-partition HPC batch-queue model (report sections 2–4).

    Each partition is an M/G/c/N/FIFO queue with log-normal service (G).
    A single Poisson arrival stream is split across partitions by `weights`,
    encoding walltime-based routing with over-declaration bias toward Standard.
    """
    print("\n" + "=" * 72)
    print("HPC BATCH-QUEUE SIMULATION  —  3 partitions, M/G/c/N/FIFO + aging")
    print("=" * 72)

    random.seed(seed)
    sim = Simulator()

    # Per-partition service distribution (G = log-normal, report SD_01).
    # SD_01 pins mean=2h, cv=1.5; we use a common service law across partitions
    # so the load imbalance is driven purely by routing weights vs (c, N).
    svc = lambda: lognormal(service_mean_h, service_cv)

    # Partitions: Short / Standard / Long  (report §2.1).
    # Created Short-first so the higher partitions can reference promote_to.
    short = QueueModel(sim, "Short", arrival_dist=None, service_dist=svc(),
                       servers=16, capacity=50, discipline='FIFO')

    standard = QueueModel(sim, "Standard", arrival_dist=None, service_dist=svc(),
                          servers=64, capacity=200, discipline='FIFO',
                          t_age=(6.0 if aging else None),
                          promote_to=(short if aging else None))

    long = QueueModel(sim, "Long", arrival_dist=None, service_dist=svc(),
                      servers=32, capacity=100, discipline='FIFO',
                      t_age=(24.0 if aging else None),
                      promote_to=(standard if aging else None))

    partitions = [short, standard, long]

    router = Router(sim, partitions=partitions, weights=list(weights),
                    arrival_dist=exponential(arrival_lambda))

    # Total nominal service capacity for context (c / mean per partition).
    mu = 1.0 / service_mean_h
    total_capacity = sum(p.servers * mu for p in partitions)
    rho_total = arrival_lambda / total_capacity

    print("\nParameters:")
    print(f"  Arrival rate λ:        {arrival_lambda} jobs/h (Poisson)")
    print(f"  Service S:             log-normal, mean={service_mean_h} h, CV={service_cv}")
    print(f"  Routing weights:       Short={weights[0]}, Standard={weights[1]}, Long={weights[2]}")
    print(f"  System capacity:       {total_capacity:.2f} jobs/h  →  offered ρ_total = {rho_total:.3f}")
    print(f"  Aging promotion:       {'ON' if aging else 'OFF'}"
          + (" (Std→Short @6h, Long→Std @24h)" if aging else ""))

    print("\nRunning simulation...")
    router.start()
    sim.run(until=until)

    print(f"\nSimulation completed at clock = {sim.clock:.1f} h")
    print(f"Total exogenous arrivals: {router.total_arrivals}")
    print(f"Routed → Short: {router.routed[0]}, Standard: {router.routed[1]}, Long: {router.routed[2]}")

    for p in partitions:
        print("\n" + "-" * 72)
        print_queue_stats(p)


def run_single_queue_test():
    """Simple M/M/1 test for validation against closed-form theory."""
    print("\n" + "=" * 72)
    print("VALIDATION TEST  —  single M/M/1 queue vs. theory")
    print("=" * 72)

    random.seed(42)
    sim = Simulator()

    lambda_rate = 1.5
    mu_rate = 2.0

    q = QueueModel(
        sim=sim,
        name="M/M/1",
        arrival_dist=exponential(lambda_rate),
        service_dist=exponential(mu_rate),
        servers=1,
        capacity=float('inf'),
        discipline='FIFO'
    )

    print(f"\nParameters: M/M/1 with λ={lambda_rate}, μ={mu_rate}")
    q.start_generator()
    sim.run(until=5000.0)

    rho = lambda_rate / mu_rate
    print("\nResults:")
    print_queue_stats(q)

    theoretical = validate_mm1(rho)
    if "error" not in theoretical:
        theoretical_wait_time = theoretical['avg_wait_in_queue'] / mu_rate
        print(f"\nComparison with theory (ρ={rho:.4f}):")
        print(f"  Simulated avg wait:   {q.avg_wait_time():.6f}")
        print(f"  Theoretical avg wait: {theoretical_wait_time:.6f}")
        print(f"  Error: {abs(q.avg_wait_time() - theoretical_wait_time) / theoretical_wait_time * 100:.2f}%")


if __name__ == "__main__":
    run_single_queue_test()
    run_hpc_cluster()
