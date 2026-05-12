"""Flask application factory for the Web Trainer.

Usage (standalone):
    python -m src.web_trainer.app

Usage (threaded):
    from src.web_trainer.app import start_trainer
    t = start_trainer(port=5000)
"""
from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path

from flask import Flask

logger = logging.getLogger(__name__)

_HERE = Path(__file__).resolve().parent          # src/web_trainer/
_ROOT = _HERE.parent.parent                      # robot_voice/


def _from_json_safe(value: str) -> list:
    """Jinja2 filter: safely parse a JSON string, return list or []."""
    if not value:
        return []
    try:
        result = json.loads(value)
        return result if isinstance(result, list) else []
    except Exception:
        return []


def create_app(db_path: str | None = None) -> Flask:
    """Create and configure the Flask application."""
    app = Flask(
        __name__,
        template_folder=str(_HERE / "templates"),
        static_folder=str(_HERE / "static"),
    )
    app.secret_key = os.environ.get("TRAINER_SECRET_KEY", "hotel-trainer-dev-key-change-me")

    # Store db_path on app config so routes can pick it up
    if db_path:
        app.config["TRAINER_DB_PATH"] = db_path

    # Register custom Jinja2 filters
    app.jinja_env.filters["from_json_safe"] = _from_json_safe

    # Register all blueprints / routes
    from src.web_trainer.routes import bp  # noqa: PLC0415
    app.register_blueprint(bp)

    return app


def start_trainer(
    port: int = 5000,
    host: str = "0.0.0.0",
    db_path: str | None = None,
    debug: bool = False,
) -> threading.Thread:
    """Start Flask in a daemon thread. Returns the thread."""
    app = create_app(db_path=db_path)

    def _run() -> None:
        logger.info("Web Trainer starting on http://%s:%d", host, port)
        # use_reloader=False is mandatory when running inside a thread
        app.run(host=host, port=port, debug=debug, use_reloader=False, threaded=True)

    t = threading.Thread(target=_run, daemon=True, name="WebTrainer")
    t.start()
    return t


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
