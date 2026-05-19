import threading
import heapq
import tkinter as tk
from typing import Callable
from time import monotonic

class HarnessTkScheduler:
    """Thread-safe scheduler for Tk callbacks during tests."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.main_thread_id = threading.get_ident()
        self._lock = threading.Lock()
        self._pending: list[tuple[float, str, Callable, tuple]] = []
        self._cancelled: set[str] = set()
        self._counter = 0
        self._installed = False

        self._orig_after = None
        self._orig_after_idle = None
        self._orig_after_cancel = None

        self.enqueued_count = 0
        self.executed_count = 0
        self.failures: list[str] = []

    def install(self) -> None:
        """Install Tk monkeypatches for thread-safe scheduling."""
        if self._installed:
            return

        self._orig_after = tk.Misc.after
        self._orig_after_idle = tk.Misc.after_idle
        self._orig_after_cancel = tk.Misc.after_cancel

        scheduler = self
        orig_after = self._orig_after
        orig_after_idle = self._orig_after_idle
        orig_after_cancel = self._orig_after_cancel

        def patched_after(self, ms, func=None, *args):
            if func is None:
                func = lambda: None
                args = ()

            if threading.get_ident() == scheduler.main_thread_id:
                return orig_after(self, ms, func, *args)

            try:
                delay_ms = int(ms)
            except Exception:
                delay_ms = 0

            with scheduler._lock:
                token = f"harness-after-{scheduler._counter}"
                scheduler._counter += 1
                scheduler.enqueued_count += 1
                heapq.heappush(
                    scheduler._pending,
                    (monotonic() + max(delay_ms, 0) / 1000.0, token, func, args),
                )

            return token

        def patched_after_idle(self, func, *args):
            if threading.get_ident() == scheduler.main_thread_id:
                return orig_after_idle(self, func, *args)

            with scheduler._lock:
                token = f"harness-after-{scheduler._counter}"
                scheduler._counter += 1
                scheduler.enqueued_count += 1
                heapq.heappush(scheduler._pending, (monotonic(), token, func, args))

            return token

        def patched_after_cancel(self, id):
            if isinstance(id, str) and id.startswith("harness-after-"):
                with scheduler._lock:
                    scheduler._cancelled.add(id)
                return None

            return orig_after_cancel(self, id)

        tk.Misc.after = patched_after  # type: ignore[assignment]
        tk.Misc.after_idle = patched_after_idle  # type: ignore[assignment]
        tk.Misc.after_cancel = patched_after_cancel  # type: ignore[assignment]
        self._installed = True

    def uninstall(self) -> None:
        """Restore original Tk behavior."""
        if not self._installed:
            return

        if self._orig_after is not None:
            tk.Misc.after = self._orig_after
        if self._orig_after_idle is not None:
            tk.Misc.after_idle = self._orig_after_idle
        if self._orig_after_cancel is not None:
            tk.Misc.after_cancel = self._orig_after_cancel

        self._installed = False

    def pending_count(self) -> int:
        with self._lock:
            return len(self._pending)

    def drain_due_callbacks(self) -> int:
        """Run all queued callbacks that are due on the main thread."""
        if threading.get_ident() != self.main_thread_id:
            return 0

        now = monotonic()
        ready: list[tuple[str, Callable, tuple]] = []

        with self._lock:
            while self._pending and self._pending[0][0] <= now:
                _, token, func, args = heapq.heappop(self._pending)
                ready.append((token, func, args))

        ran = 0
        for token, func, args in ready:
            with self._lock:
                if token in self._cancelled:
                    self._cancelled.remove(token)
                    continue

            try:
                func(*args)
                ran += 1
                self.executed_count += 1
            except Exception as exc:
                self.failures.append(f"Scheduler callback {token}: {type(exc).__name__}: {exc}")

        return ran

    def consume_failures(self) -> list[str]:
        failures = self.failures[:]
        self.failures.clear()
        return failures
