import heapq
from typing import Callable
from event import Event


class Simulator:
    """The central event scheduler."""
    def __init__(self):
        self.clock = 0.0
        self.event_calendar = []

    def schedule(self, time: float, event_type: str, action: Callable, entity: dict = None):
        event = Event(time, event_type, action, entity)
        heapq.heappush(self.event_calendar, event)

    def run(self, until: float):
        while self.event_calendar and self.clock < until:
            event = heapq.heappop(self.event_calendar)
            self.clock = event.time
            if self.clock > until:
                break
            event.action(event)
