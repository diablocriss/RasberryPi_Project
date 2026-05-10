from __future__ import annotations

import logging
import queue
import threading
from pathlib import Path
from typing import Any

from db.booking_bridge import BookingLib

logger = logging.getLogger(__name__)


class FutureEvent:
    """Small future used to hand results back to the caller thread."""

    def __init__(self) -> None:
        self._event = threading.Event()
        self._result: Any = None
        self._exception: BaseException | None = None

    def set_result(self, result: Any) -> None:
        self._result = result
        self._event.set()

    def set_exception(self, exc: BaseException) -> None:
        self._exception = exc
        self._event.set()

    def wait(self, timeout: float = 5.0) -> Any:
        if not self._event.wait(timeout):
            raise TimeoutError("DB operation timed out")
        if self._exception is not None:
            raise self._exception
        return self._result


class DBWorker:
    def __init__(self, so_path: str | Path, db_path: str | Path) -> None:
        self._so_path = str(Path(so_path).expanduser())
        self._db_path = str(Path(db_path).expanduser())
        self._queue: queue.Queue[tuple[str, dict[str, Any], FutureEvent] | None] = queue.Queue()
        self._ready = threading.Event()
        self._startup_error: BaseException | None = None
        self._running = True
        self._lib: BookingLib | None = None
        self._thread = threading.Thread(target=self._run, daemon=True, name="DBWorker")
        self._thread.start()
        self._ready.wait(timeout=5.0)
        if self._startup_error is not None:
            raise RuntimeError(f"DBWorker failed to start: {self._startup_error}") from self._startup_error
        if self._lib is None:
            raise RuntimeError("DBWorker failed to initialise")
        logger.info("DBWorker started (db=%s, lib=%s)", self._db_path, self._so_path)

    def _run(self) -> None:
        try:
            self._lib = BookingLib(self._so_path)
            rc = self._lib.storage_init(self._db_path)
            if rc != 0:
                raise RuntimeError(f"storage_init failed with code {rc}")
        except BaseException as exc:
            self._startup_error = exc
            self._ready.set()
            return

        self._ready.set()

        try:
            while self._running:
                try:
                    item = self._queue.get(timeout=1.0)
                except queue.Empty:
                    continue

                if item is None:
                    break

                op, kwargs, future = item
                try:
                    method = getattr(self._lib, op)
                    future.set_result(method(**kwargs))
                except BaseException as exc:
                    logger.exception("DB operation %s failed", op)
                    future.set_exception(exc)
        finally:
            if self._lib is not None:
                self._lib.storage_close()
            logger.info("DBWorker shut down")

    def _enqueue(self, op: str, **kwargs: Any) -> FutureEvent:
        future = FutureEvent()
        if self._startup_error is not None:
            future.set_exception(RuntimeError("DBWorker is unavailable"))
            return future
        self._queue.put((op, kwargs, future))
        return future

    def create_booking(
        self,
        guest_name: str,
        email: str = "",
        check_in: str = "",
        check_out: str = "",
        guests: int = 1,
        room_id: int = 1,
    ) -> FutureEvent:
        return self._enqueue(
            "create_booking",
            guest_name=guest_name,
            email=email,
            check_in=check_in,
            check_out=check_out,
            guests=guests,
            room_id=room_id,
        )

    def cancel_booking(self, booking_id: int) -> FutureEvent:
        return self._enqueue("cancel_booking", booking_id=booking_id)

    def list_bookings(self) -> FutureEvent:
        return self._enqueue("list_bookings")

    def list_rooms(self) -> FutureEvent:
        return self._enqueue("list_rooms")

    def check_availability(self, check_in: str, check_out: str) -> FutureEvent:
        return self._enqueue("check_availability", check_in=check_in, check_out=check_out)

    def check_conflict(self, room_id: int, check_in: str, check_out: str) -> FutureEvent:
        return self._enqueue(
            "check_conflict",
            room_id=room_id,
            check_in=check_in,
            check_out=check_out,
        )

    def shutdown(self) -> None:
        if not self._thread.is_alive():
            return
        self._running = False
        self._queue.put(None)
        self._thread.join(timeout=3.0)
