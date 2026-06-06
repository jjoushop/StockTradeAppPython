from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from time import time


@dataclass(frozen=True)
class ThreadSnapshot:
    name: str
    iterations: int
    last_heartbeat_epoch_seconds: float
    status: str


class SharedMemory:
    """Small thread-safe shared state container for worker coordination."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._state: dict[str, ThreadSnapshot] = {}
        self._events: list[str] = []

    def mark_started(self, thread_name: str) -> None:
        with self._lock:
            self._state[thread_name] = ThreadSnapshot(
                name=thread_name,
                iterations=0,
                last_heartbeat_epoch_seconds=time(),
                status="running",
            )
            self._events.append(f"{thread_name} started")

    def heartbeat(self, thread_name: str) -> int:
        with self._lock:
            current = self._state.get(thread_name)
            next_iteration = 1 if current is None else current.iterations + 1
            self._state[thread_name] = ThreadSnapshot(
                name=thread_name,
                iterations=next_iteration,
                last_heartbeat_epoch_seconds=time(),
                status="running",
            )
            return next_iteration

    def mark_stopped(self, thread_name: str) -> None:
        with self._lock:
            current = self._state.get(thread_name)
            iterations = 0 if current is None else current.iterations
            self._state[thread_name] = ThreadSnapshot(
                name=thread_name,
                iterations=iterations,
                last_heartbeat_epoch_seconds=time(),
                status="stopped",
            )
            self._events.append(f"{thread_name} stopped")

    def snapshots(self) -> tuple[ThreadSnapshot, ...]:
        with self._lock:
            return tuple(self._state[name] for name in sorted(self._state))

    def events(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(self._events)
