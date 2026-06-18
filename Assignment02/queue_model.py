from collections import deque
from typing import Callable, Optional
from simulator import Simulator
from event import Event
import random


class QueueModel:
    """Represents a single queue based on Kendall's Notation (A/S/c/N/D)."""
    def __init__(self,
                 sim: Simulator,
                 name: str,
                 arrival_dist: Callable[[], float],
                 service_dist: Callable[[], float],
                 servers: int = 1,
                 capacity: float = float('inf'),
                 discipline: str = 'FIFO',
                 next_queue: Optional['QueueModel'] = None,
                 t_age: Optional[float] = None,
                 promote_to: Optional['QueueModel'] = None):
        self.sim = sim
        self.name = name
        self.arrival_dist = arrival_dist
        self.service_dist = service_dist
        self.servers = servers
        self.capacity = capacity
        self.discipline = discipline
        self.next_queue = next_queue
        # Aging / priority promotion: a job that has
        # waited longer than t_age is promoted into promote_to, bypassing that
        # partition's admission gateway.
        self.t_age = t_age
        self.promote_to = promote_to

        self.queue = deque()
        self.busy_servers = 0

        # Statistics
        self.entities_processed = 0
        self.entities_dropped = 0
        self.entities_promoted = 0
        self.wait_times = []  # Track wait time for each job
        self.queue_lengths = []  # Track (time, queue_length) snapshots
        self.total_busy_time = 0.0  # Cumulative server busy time
        self.last_event_time = 0.0  # For busy time calculation

    def reset_statistics(self):
        """Reset all statistical counters without disturbing the model state.

        Mirrors GPSS World's RESET command: the queue contents and busy
        servers are preserved (the system stays in its current state), but
        all accumulators are zeroed so that subsequent collection starts
        from a warm, steady-state baseline.
        """
        self.entities_processed = 0
        self.entities_dropped = 0
        self.entities_promoted = 0
        self.wait_times = []
        self.queue_lengths = [(self.sim.clock, len(self.queue))]
        self.total_busy_time = 0.0
        self.last_event_time = self.sim.clock

    def start_generator(self):
        """Kickstarts the arrival process."""
        first_arrival_time = self.sim.clock + self.arrival_dist()
        self.sim.schedule(first_arrival_time, "Arrival", self._handle_arrival)

    def _handle_arrival(self, event: Event):
        # 1. Schedule the next exogenous arrival
        if event.event_type == "Arrival":
            next_arrival_time = self.sim.clock + self.arrival_dist()
            self.sim.schedule(next_arrival_time, "Arrival", self._handle_arrival)

        # 2. Process current entity
        entity = event.entity or {"id": random.randint(1000, 9999), "arrival_time": self.sim.clock}
        
        # Record queue length snapshot
        self.queue_lengths.append((self.sim.clock, len(self.queue)))

        # Check capacity (N). Promoted jobs carry bypass_capacity and skip the
        # admission gateway (report SS_03): they always enter.
        bypass = entity.pop("bypass_capacity", False)
        total_in_system = len(self.queue) + self.busy_servers
        if not bypass and total_in_system >= self.capacity:
            self.entities_dropped += 1
            return  # Entity is blocked

        if self.busy_servers < self.servers:
            # Server is available, go straight to service
            self.busy_servers += 1
            entity["service_start_time"] = self.sim.clock
            self._schedule_departure(entity)
        else:
            # Wait in queue
            if self.discipline == 'LIFO':
                self.queue.appendleft(entity)
            else:
                self.queue.append(entity)  # FIFO (and default)
            # Arm the aging timer for this waiting job.
            if self.t_age is not None and self.promote_to is not None:
                self.sim.schedule(self.sim.clock + self.t_age, "Promotion",
                                  self._handle_promotion, entity)

    def _schedule_departure(self, entity: dict):
        departure_time = self.sim.clock + self.service_dist()
        self.sim.schedule(departure_time, "Departure", self._handle_departure, entity)

    def _handle_departure(self, event: Event):
        entity = event.entity
        self.entities_processed += 1
        
        # Calculate and track wait time
        if "arrival_time" in entity and "service_start_time" in entity:
            wait_time = entity["service_start_time"] - entity["arrival_time"]
            self.wait_times.append(wait_time)
            # Track total busy time
            service_time = self.sim.clock - entity["service_start_time"]
            self.total_busy_time += service_time
        
        # 1. Forward to next queue if modular, else entity leaves system
        if self.next_queue:
            # Send it to the next queue immediately (reset service_start_time)
            if "service_start_time" in entity:
                del entity["service_start_time"]
            self.next_queue.sim.schedule(self.sim.clock, "Transfer", self.next_queue._handle_arrival, entity)

        # 2. Check if waiting entities can take the freed server
        if len(self.queue) > 0:
            if self.discipline == 'SIRO':
                # Service In Random Order
                idx = random.randint(0, len(self.queue) - 1)
                next_entity = self.queue[idx]
                del self.queue[idx]
            else:
                next_entity = self.queue.popleft()  # Handles both FIFO/LIFO
            
            next_entity["service_start_time"] = self.sim.clock
            self._schedule_departure(next_entity)
        else:
            self.busy_servers -= 1

    def _handle_promotion(self, event: Event):
        """Fire the aging timer: promote the job if it is still waiting.

        If the job already entered service (or already left) it is no longer in
        the waiting deque, so the timer is a no-op.
        """
        entity = event.entity
        # Locate the job in the waiting deque by identity.
        idx = next((i for i, e in enumerate(self.queue) if e is entity), None)
        if idx is None:
            return  # Job already started service; nothing to promote.

        del self.queue[idx]
        self.entities_promoted += 1
        # Bypass the target partition's admission gateway and inject now.
        entity["bypass_capacity"] = True
        self.promote_to.sim.schedule(self.sim.clock, "Promotion",
                                     self.promote_to._handle_arrival, entity)

    def avg_wait_time(self) -> float:
        """Average wait time (excluding jobs still in queue)."""
        if not self.wait_times:
            return 0.0
        return sum(self.wait_times) / len(self.wait_times)

    def avg_queue_length(self) -> float:
        """Average queue length over the simulation."""
        if len(self.queue_lengths) < 2:
            return 0.0
        total_time = 0.0
        weighted_sum = 0.0
        for i in range(len(self.queue_lengths) - 1):
            t1, q1 = self.queue_lengths[i]
            t2, q2 = self.queue_lengths[i + 1]
            dt = t2 - t1
            total_time += dt
            weighted_sum += q1 * dt
        if total_time == 0:
            return 0.0
        return weighted_sum / total_time

    def utilization(self) -> float:
        """Server utilization (ρ = total_busy_time / (total_time * servers))."""
        total_time = self.sim.clock
        if total_time == 0:
            return 0.0
        return self.total_busy_time / (total_time * self.servers)

    def throughput(self) -> float:
        """Throughput (jobs per unit time)."""
        total_time = self.sim.clock
        if total_time == 0:
            return 0.0
        return self.entities_processed / total_time

    def drop_rate(self) -> float:
        """Drop/loss rate (proportion of dropped jobs)."""
        total_arrivals = self.entities_processed + self.entities_dropped
        if total_arrivals == 0:
            return 0.0
        return self.entities_dropped / total_arrivals

    def blocking_probability(self) -> float:
        """P_b: fraction of admission attempts blocked by the capacity gate."""
        return self.drop_rate()


class Router:
    """Routes a single Poisson arrival stream across N partitions.

    Implements the BPMN exclusive gateway: each exogenous job is routed to one
    partition according to a categorical distribution over `weights`. For the
    HPC model this distribution encodes walltime-based routing (with the
    over-declaration bias toward Standard baked into the weights).
    """
    def __init__(self,
                 sim: Simulator,
                 partitions: list,
                 weights: list,
                 arrival_dist: Callable[[], float] = None,
                 rng=None):
        if len(partitions) != len(weights):
            raise ValueError("partitions and weights must have equal length")
        self.sim = sim
        self.partitions = partitions
        total = float(sum(weights))
        self.weights = [w / total for w in weights]
        self.arrival_dist = arrival_dist or (lambda: 1.0)
        # Routing draws from the same custom-LCG stream as arrivals
        # (report stream 1 = arrivals + routing). Required, not optional.
        if rng is None:
            raise ValueError("Router requires a custom RNG (util.LCG) for routing")
        self.rng = rng

        self.total_arrivals = 0
        self.routed = [0] * len(partitions)

    def start(self):
        """Kick-start the exogenous arrival process."""
        first_arrival_time = self.sim.clock + self.arrival_dist()
        self.sim.schedule(first_arrival_time, "ExogenousArrival",
                          self._handle_exogenous_arrival)

    def _pick_partition(self) -> int:
        r = self.rng.random()
        cum = 0.0
        for i, w in enumerate(self.weights):
            cum += w
            if r < cum:
                return i
        return len(self.weights) - 1

    def _handle_exogenous_arrival(self, event: Event):
        """Handle one exogenous job arrival and route it to a partition."""
        # Schedule the next exogenous arrival.
        next_arrival_time = self.sim.clock + self.arrival_dist()
        self.sim.schedule(next_arrival_time, "ExogenousArrival",
                          self._handle_exogenous_arrival)

        # Create the job entity.
        entity = {
            "id": self.total_arrivals,
            "arrival_time": self.sim.clock,
        }
        self.total_arrivals += 1

        idx = self._pick_partition()
        self.routed[idx] += 1
        self.sim.schedule(self.sim.clock, "Transfer",
                          self.partitions[idx]._handle_arrival, entity)
