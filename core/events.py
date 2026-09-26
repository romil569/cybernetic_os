from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from threading import RLock
from time import time
from typing import Any, Callable


@dataclass(frozen=True)
class Event:
    name: str
    payload: Any
    timestamp: float


class EventBus:
    """Small synchronous bus; ownership stays with the application loop."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[Callable[[Event], None]]] = defaultdict(list)
        self._lock = RLock()

    def subscribe(self, name: str, handler: Callable[[Event], None]) -> Callable[[], None]:
        with self._lock:
            self._handlers[name].append(handler)

        def unsubscribe() -> None:
            with self._lock:
                if handler in self._handlers[name]:
                    self._handlers[name].remove(handler)

        return unsubscribe

    def publish(self, name: str, payload: Any) -> Event:
        event = Event(name=name, payload=payload, timestamp=time())
        with self._lock:
            handlers = tuple(self._handlers[name])
        for handler in handlers:
            handler(event)
        return event
