from typing import Callable

# Tie-breaking priority for simultaneous events.
# Lower value = processed first.
# Physical rationale:
#   Departures free a server before new arrivals compete for it.
#   Promotions are rescheduling events and yield to both.
_TYPE_PRIORITY = {
    "Departure":        0,
    "Arrival":          1,
    "ExogenousArrival": 1,
    "Transfer":         1,
    "Promotion":        2,
}
_DEFAULT_PRIORITY = 1  # fallback for any future event types


class Event:
    """Represents an event in the discrete-event simulation.

    Ordering is by (time, priority) so that simultaneous events are resolved
    in a physically meaningful way: Departures before Arrivals/Transfers,
    Arrivals/Transfers before Promotions.
    """
    def __init__(self, time: float, event_type: str, action: Callable, entity: dict = None):
        self.time = time
        self.event_type = event_type
        self.action = action
        self.entity = entity
        self.priority = _TYPE_PRIORITY.get(event_type, _DEFAULT_PRIORITY)

    def __lt__(self, other: "Event") -> bool:
        # Primary key: simulation time.
        # Secondary key: event-type priority (Departure < Arrival < Promotion).
        if self.time != other.time:
            return self.time < other.time
        return self.priority < other.priority

    def __le__(self, other: "Event") -> bool:
        if self.time != other.time:
            return self.time < other.time
        return self.priority <= other.priority