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
                 next_queue: Optional['QueueModel'] = None):
        self.sim = sim
        self.name = name
        self.arrival_dist = arrival_dist
        self.service_dist = service_dist
        self.servers = servers
        self.capacity = capacity
        self.discipline = discipline
        self.next_queue = next_queue
        
        self.queue = deque()
        self.busy_servers = 0
        
        # Statistics
        self.entities_processed = 0
        self.entities_dropped = 0
        self.wait_times = []  # Track wait time for each job
        self.queue_lengths = []  # Track (time, queue_length) snapshots
        self.total_busy_time = 0.0  # Cumulative server busy time
        self.last_event_time = 0.0  # For busy time calculation

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
        
        # Check capacity
        total_in_system = len(self.queue) + self.busy_servers
        if total_in_system >= self.capacity:
            self.entities_dropped += 1
            return  # Entity is dropped

        if self.busy_servers < self.servers:
            # Server is available, go straight to service
            self.busy_servers += 1
            entity["service_start_time"] = self.sim.clock
            self._schedule_departure(entity)
        else:
            # Wait in queue
            if self.discipline == 'FIFO':
                self.queue.append(entity)
            elif self.discipline == 'LIFO':
                self.queue.appendleft(entity)
            else:
                self.queue.append(entity)  # Default to FIFO

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


class Router:
    """Routes jobs to multiple queues based on a probability distribution.
    
    Implements the Dispatcher lane from BPMN: exogenous arrivals split
    between Standard and Priority classes with probability (1-p) and p.
    """
    def __init__(self,
                 sim: Simulator,
                 std_queue: QueueModel,
                 pri_queue: QueueModel,
                 prob_priority: float = 0.5,
                 arrival_dist: Callable[[], float] = None):
        """Initialize the router.
        
        Args:
            sim: The Simulator instance
            std_queue: Standard priority queue
            pri_queue: Priority queue
            prob_priority: Probability of routing to priority queue (0 to 1)
            arrival_dist: Arrival time distribution for exogenous arrivals
        """
        self.sim = sim
        self.std_queue = std_queue
        self.pri_queue = pri_queue
        self.prob_priority = prob_priority
        self.arrival_dist = arrival_dist or (lambda: 1.0)  # Default: 1 per unit time
        
        self.total_arrivals = 0

    def start(self):
        """Kick-start the arrival process."""
        first_arrival_time = self.sim.clock + self.arrival_dist()
        self.sim.schedule(first_arrival_time, "ExogenousArrival", self._handle_exogenous_arrival)

    def _handle_exogenous_arrival(self, event: Event):
        """Handle exogenous job arrival and route to Standard or Priority."""
        # Schedule next arrival
        next_arrival_time = self.sim.clock + self.arrival_dist()
        self.sim.schedule(next_arrival_time, "ExogenousArrival", self._handle_exogenous_arrival)

        # Create job entity
        job_id = self.total_arrivals
        self.total_arrivals += 1
        entity = {
            "id": job_id,
            "arrival_time": self.sim.clock,
            "is_priority": random.random() < self.prob_priority
        }

        # Route to appropriate queue
        target_queue = self.pri_queue if entity["is_priority"] else self.std_queue
        self.sim.schedule(self.sim.clock, "Transfer", target_queue._handle_arrival, entity)


