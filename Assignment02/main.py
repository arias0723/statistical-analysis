from util import *
from simulator import Simulator
from queue_model import QueueModel, Router
import math


def validate_mm1(rho: float) -> dict:
    """Compute theoretical M/M/1 performance metrics.
    
    Args:
        rho: utilization = λ / μ (must be < 1)
    
    Returns:
        dict with theoretical values: avg_wait_in_queue, avg_queue_length, etc.
    """
    if rho >= 1:
        return {"error": "M/M/1 unstable (ρ >= 1)"}
    
    # M/M/1 formulas
    avg_wait_in_queue = rho / (1 - rho)  # in units of 1/μ
    avg_queue_length = rho**2 / (1 - rho)
    avg_wait_in_system = 1 / (1 - rho)  # in units of 1/μ
    
    return {
        "rho": rho,
        "avg_wait_in_queue": avg_wait_in_queue,
        "avg_queue_length": avg_queue_length,
        "avg_wait_in_system": avg_wait_in_system,
    }


def print_queue_stats(queue: QueueModel):
    """Pretty-print statistics for a single queue."""
    print(f"  Queue: {queue.name}")
    print(f"    Processed: {queue.entities_processed}")
    print(f"    Dropped: {queue.entities_dropped}")
    print(f"    Throughput (jobs/unit time): {queue.throughput():.6f}")
    print(f"    Avg wait time (in queue): {queue.avg_wait_time():.6f}")
    print(f"    Avg queue length: {queue.avg_queue_length():.6f}")
    print(f"    Server utilization (ρ): {queue.utilization():.6f}")
    print(f"    Drop rate: {queue.drop_rate():.6f}")


def run_network_simulation():
    """Run the HPC cluster scheduler with Standard + Priority queues."""
    print("\n" + "="*70)
    print("HPC CLUSTER SCHEDULER SIMULATION")
    print("="*70)
    
    random.seed(42)
    sim = Simulator()

    # Define queue parameters
    # Arrival rate λ = 2 (mean interarrival = 0.5)
    arrival_lambda = 2.0
    
    # Standard queue: M/M/1, service rate μ = 3
    service_mu_std = 3.0
    
    # Priority queue: M/M/2, service rate μ = 2 per server (c=2 servers)
    service_mu_pri = 2.0
    c_pri = 2
    
    # Class routing probability
    prob_priority = 0.3  # 30% priority, 70% standard
    
    # Create queues
    std_queue = QueueModel(
        sim=sim,
        name="Standard",
        arrival_dist=exponential(arrival_lambda),
        service_dist=exponential(service_mu_std),
        servers=1,
        capacity=float('inf'),
        discipline='FIFO'
    )
    
    pri_queue = QueueModel(
        sim=sim,
        name="Priority",
        arrival_dist=exponential(arrival_lambda * prob_priority),  # Theoretical split
        service_dist=exponential(service_mu_pri),
        servers=c_pri,
        capacity=float('inf'),
        discipline='FIFO'
    )
    
    # Create router
    router = Router(
        sim=sim,
        std_queue=std_queue,
        pri_queue=pri_queue,
        prob_priority=prob_priority,
        arrival_dist=exponential(arrival_lambda)
    )
    
    # Run simulation
    print("\nParameters:")
    print(f"  Exogenous arrival rate (λ): {arrival_lambda} jobs/unit time")
    print(f"  Standard queue: M/M/1, service rate μ = {service_mu_std}")
    print(f"  Priority queue: M/M/{c_pri}, service rate μ = {service_mu_pri}")
    print(f"  Routing: P(priority) = {prob_priority}, P(standard) = {1-prob_priority}")
    
    print("\nRunning simulation...")
    router.start()
    sim.run(until=10000.0)
    
    print(f"\nSimulation completed at clock time = {sim.clock:.2f}")
    print(f"Total exogenous arrivals: {router.total_arrivals}")
    
    # Print results
    print("\n" + "-"*70)
    print("STANDARD QUEUE STATISTICS:")
    print("-"*70)
    print_queue_stats(std_queue)
    
    print("\n" + "-"*70)
    print("PRIORITY QUEUE STATISTICS:")
    print("-"*70)
    print_queue_stats(pri_queue)
    
    # Validation: compare with M/M/1 theory for Standard queue
    print("\n" + "-"*70)
    print("VALIDATION: STANDARD QUEUE vs. M/M/1 THEORY")
    print("-"*70)
    lambda_std_effective = std_queue.throughput()
    mu_std = service_mu_std
    rho_std = lambda_std_effective / mu_std
    
    print(f"  Simulated arrival rate: {lambda_std_effective:.6f}")
    print(f"  Service rate: {mu_std:.6f}")
    print(f"  Simulated ρ (utilization): {rho_std:.6f}")
    
    theoretical = validate_mm1(rho_std)
    if "error" not in theoretical:
        print(f"\n  Theoretical M/M/1 (ρ={rho_std:.6f}):")
        print(f"    Avg wait (in queue, units of 1/μ): {theoretical['avg_wait_in_queue']:.6f}")
        print(f"    Avg queue length: {theoretical['avg_queue_length']:.6f}")
        
        # For comparison, scale theoretical wait back to original time units
        # If service time ~ Exp(μ), then mean = 1/μ
        # So actual avg wait = theoretical * (1/μ)
        theoretical_wait_time = theoretical['avg_wait_in_queue'] / mu_std
        print(f"    Avg wait (in time units): {theoretical_wait_time:.6f}")
        
        print(f"\n  Simulation vs. Theory:")
        print(f"    Simulated avg wait: {std_queue.avg_wait_time():.6f}")
        print(f"    Theoretical avg wait: {theoretical_wait_time:.6f}")
        print(f"    Difference: {abs(std_queue.avg_wait_time() - theoretical_wait_time):.6f}")
        print(f"    Simulated avg queue length: {std_queue.avg_queue_length():.6f}")
        print(f"    Theoretical avg queue length: {theoretical['avg_queue_length']:.6f}")
        print(f"    Difference: {abs(std_queue.avg_queue_length() - theoretical['avg_queue_length']):.6f}")


def run_single_queue_test():
    """Simple M/M/1 test for validation against theory."""
    print("\n" + "="*70)
    print("SIMPLE M/M/1 TEST")
    print("="*70)
    
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
    print(f"\nResults:")
    print_queue_stats(q)
    
    theoretical = validate_mm1(rho)
    if "error" not in theoretical:
        theoretical_wait_time = theoretical['avg_wait_in_queue'] / mu_rate
        print(f"\nComparison with theory (ρ={rho:.4f}):")
        print(f"  Simulated avg wait: {q.avg_wait_time():.6f}")
        print(f"  Theoretical avg wait: {theoretical_wait_time:.6f}")
        print(f"  Error: {abs(q.avg_wait_time() - theoretical_wait_time) / theoretical_wait_time * 100:.2f}%")


if __name__ == "__main__":
    # Run both tests
    run_single_queue_test()
    run_network_simulation()

