import heapq
from typing import Callable
from event import Event


class Simulator:
    """The central event scheduler.

    Supports an optional trace mode that logs the first N events to a list
    for manual verification (report Section 9 — trace validation).
    """
    def __init__(self, trace_limit: int = 0):
        self.clock = 0.0
        self.event_calendar = []
        self.trace_limit = trace_limit
        self.trace_log = []
        self._trace_count = 0

    def schedule(self, time: float, event_type: str, action: Callable, entity: dict = None):
        event = Event(time, event_type, action, entity)
        heapq.heappush(self.event_calendar, event)

    def run(self, until: float):
        while self.event_calendar and self.clock < until:
            event = heapq.heappop(self.event_calendar)
            self.clock = event.time
            if self.clock > until:
                break

            # Trace logging: capture state before executing the event
            if self._trace_count < self.trace_limit:
                self._record_trace(event)

            event.action(event)

    def _record_trace(self, event: Event):
        """Record one trace row: clock, event type, entity id, calendar size."""
        entity_id = None
        if event.entity and "id" in event.entity:
            entity_id = event.entity["id"]
        self.trace_log.append({
            "step": self._trace_count,
            "clock": round(self.clock, 6),
            "event_type": event.event_type,
            "entity_id": entity_id,
            "calendar_size": len(self.event_calendar),
        })
        self._trace_count += 1

    def print_trace(self):
        """Pretty-print the trace log as a table."""
        if not self.trace_log:
            print("  (no trace recorded — set trace_limit > 0)")
            return
        header = f"  {'Step':>4}  {'Clock':>12}  {'Event Type':<18}  {'Entity':>6}  {'Calendar':>8}"
        print(header)
        print("  " + "-" * len(header))
        for row in self.trace_log:
            eid = str(row['entity_id']) if row['entity_id'] is not None else "-"
            print(f"  {row['step']:>4}  {row['clock']:>12.6f}  {row['event_type']:<18}  {eid:>6}  {row['calendar_size']:>8}")
