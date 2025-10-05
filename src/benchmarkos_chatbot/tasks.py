"""Lightweight task queue for orchestrating live ingestion jobs."""

from __future__ import annotations

import threading
from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError
from dataclasses import dataclass
from datetime import datetime
from queue import Queue
from typing import Dict, Optional

from .data_ingestion import ingest_live_tickers
from .config import Settings


@dataclass(slots=True)
class TaskStatus:
    """Lightweight task status value returned to the UI."""
    ticker: str
    years: int
    state: str
    submitted_at: datetime
    updated_at: datetime
    error: Optional[str] = None

    def summary(self) -> str:
        """Summarise an ingestion task for status displays."""
        if self.state == "failed" and self.error:
            return f"{self.state} ({self.error})"
        return self.state


class TaskManager:
    """Minimal task orchestrator for ingestion jobs."""

    def __init__(self, settings: Settings, max_workers: int = 2) -> None:
        """Initialise the background task manager and worker thread."""
        self._settings = settings
        self._queue: Queue[tuple[str, int]] = Queue()
        self._statuses: Dict[str, TaskStatus] = {}
        self._futures: Dict[str, Future] = {}
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()

    def _worker_loop(self) -> None:
        """Background loop that processes queued ingestion tasks."""
        while True:
            ticker, years = self._queue.get()
            status = self._statuses[ticker]
            future = self._futures[ticker]
            status.state = "running"
            status.updated_at = datetime.utcnow()
            try:
                result = ingest_live_tickers(self._settings, [ticker], years=years)
            except Exception as exc:  # pragma: no cover - network path
                status.state = "failed"
                status.error = str(exc)
                status.updated_at = datetime.utcnow()
                future.set_exception(exc)
            else:
                status.state = "succeeded"
                status.updated_at = datetime.utcnow()
                future.set_result(result)
            finally:
                self._queue.task_done()

    def submit_ingest(self, ticker: str, *, years: int = 5) -> Future:
        """Enqueue a new ingestion job for asynchronous execution."""
        ticker = ticker.upper()
        now = datetime.utcnow()
        existing = self._statuses.get(ticker)
        if existing and existing.state in {"pending", "running"}:
            return self._futures[ticker]

        status = TaskStatus(
            ticker=ticker,
            years=years,
            state="pending",
            submitted_at=now,
            updated_at=now,
        )
        future: Future = Future()
        self._statuses[ticker] = status
        self._futures[ticker] = future
        self._queue.put((ticker, years))
        return future

    def get_status(self, ticker: str) -> Optional[TaskStatus]:
        """Return the status of a submitted task by id."""
        return self._statuses.get(ticker.upper())

    def wait_for_completion(self, ticker: str, *, timeout: Optional[float] = None) -> None:
        """Block until a task either completes or times out."""
        future = self._futures.get(ticker.upper())
        if not future:
            return
        future.result(timeout=timeout)


_default_manager: Optional[TaskManager] = None


def get_task_manager(settings: Settings) -> TaskManager:
    """Return a singleton background task manager instance."""
    global _default_manager
    if _default_manager is None:
        _default_manager = TaskManager(settings)
    return _default_manager


def wait_until_complete(settings: Settings, ticker: str, *, timeout: Optional[float] = None) -> None:
    """Poll the task manager until outstanding work finishes."""
    manager = get_task_manager(settings)
    try:
        manager.wait_for_completion(ticker, timeout=timeout)
    except TimeoutError as exc:
        raise TimeoutError(f"Live ingestion for {ticker} is still running") from exc
