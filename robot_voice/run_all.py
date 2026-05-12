#!/usr/bin/env python3
"""run_all.py — Start voice pipeline + DB worker + Web Trainer (3 threads).

Usage:
    python run_all.py                     # all 3 systems
    TRAINER_PORT=5001 python run_all.py   # custom port
    ROBOT_DRY_RUN=1 python run_all.py     # dry-run (no real ESP32 commands)

Environment variables (all optional, override .env):
    ROBOT_BOOKING_LIB   path to libbooking.so
    ROBOT_BOOKING_DB    path to bookings.db
    TRAINER_PORT        web trainer port (default 5000)
    TRAINER_DB_PATH     path to trainer.db (default data/trainer.db)
    ROBOT_DRY_RUN       1 = dry run mode
"""
from __future__ import annotations

import logging
import os
import signal
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Ensure robot_voice/ is on sys.path when run directly
# ---------------------------------------------------------------------------
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Load .env if present
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=_ROOT / ".env", override=False)
except ImportError:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("run_all")


def main() -> None:
    lib_path  = os.environ.get("ROBOT_BOOKING_LIB",  "~/AppBookingResPi4/libbooking.so")
    db_path   = os.environ.get("ROBOT_BOOKING_DB",   "~/AppBookingResPi4/bookings.db")
    trainer_port = int(os.environ.get("TRAINER_PORT", "5000"))

    # ── Thread 1: DB Worker ────────────────────────────────────────────
    db_worker = None
    try:
        from src.core.db_worker import DBWorker
        db_worker = DBWorker(lib_path, db_path)
        logger.info("DB Worker started.")
    except Exception as exc:
        logger.warning("DB Worker unavailable (%s); continuing without it.", exc)

    # ── Thread 2: Web Trainer ──────────────────────────────────────────
    from src.web_trainer.app import start_trainer
    trainer_thread = start_trainer(port=trainer_port)
    logger.info("Web Trainer started on http://0.0.0.0:%d", trainer_port)

    # ── Thread 3 (main): Voice Pipeline ───────────────────────────────
    pipeline = None
    try:
        from src.audio.pipeline_moonshine import Pipeline
        pipeline = Pipeline(db_worker=db_worker)
        logger.info("Voice pipeline initialised.")
    except Exception as exc:
        logger.warning("Voice pipeline unavailable (%s); Web Trainer only mode.", exc)

    # ── Graceful shutdown ──────────────────────────────────────────────
    def _shutdown(sig: int, frame: object) -> None:
        logger.info("Shutting down (signal %d)…", sig)
        if pipeline is not None:
            try:
                pipeline.stop()
            except Exception:
                pass
        if db_worker is not None:
            try:
                db_worker.shutdown()
            except Exception:
                pass
        sys.exit(0)

    signal.signal(signal.SIGINT,  _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    if pipeline is not None:
        pipeline.run()   # blocks until stopped
    else:
        # No pipeline — keep main thread alive for the Web Trainer
        logger.info("Running in Web Trainer-only mode. Press Ctrl+C to stop.")
        trainer_thread.join()


if __name__ == "__main__":
    main()
