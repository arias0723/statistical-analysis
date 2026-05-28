from typing import Callable


class Event:
    """Represents an event in the simulation."""
    def __init__(self, time: float, event_type: str, action: Callable, entity: dict = None):
        self.time = time
        self.event_type = event_type
        self.action = action
        self.entity = entity

    def __lt__(self, other):
        return self.time < other.time
