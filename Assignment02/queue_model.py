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
        
        # Check capacity
        total_in_system = len(self.queue) + self.busy_servers
        if total_in_system >= self.capacity:
            self.entities_dropped += 1
            return  # Entity is dropped

        if self.busy_servers < self.servers:
            # Server is available, go straight to service
            self.busy_servers += 1
            self._schedule_departure(entity)
        else:
            # Wait in queue
            if self.discipline == 'FIFO':
                self.queue.append(entity)
            elif self.discipline == 'LIFO':
                self.queue.appendleft(entity)
            else:
                self.queue.append(entity) # Default to FIFO

    def _schedule_departure(self, entity: dict):
        departure_time = self.sim.clock + self.service_dist()
        self.sim.schedule(departure_time, "Departure", self._handle_departure, entity)

    def _handle_departure(self, event: Event):
        self.entities_processed += 1
        
        # 1. Forward to next queue if modular, else entity leaves system
        if self.next_queue:
            # Send it to the next queue immediately
            self.next_queue.sim.schedule(self.sim.clock, "Transfer", self.next_queue._handle_arrival, event.entity)

        # 2. Check if waiting entities can take the freed server
        if len(self.queue) > 0:
            if self.discipline == 'SIRO':
                # Service In Random Order
                idx = random.randint(0, len(self.queue) - 1)
                next_entity = self.queue[idx]
                del self.queue[idx]
            else:
                next_entity = self.queue.popleft() # Handles both FIFO/LIFO due to append behavior
                
            self._schedule_departure(next_entity)
        else:
            self.busy_servers -= 1
