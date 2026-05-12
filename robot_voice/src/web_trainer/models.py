"""TrainerDB — SQLite-backed data layer for the web trainer.

Uses stdlib sqlite3 only (no SQLAlchemy).
On first run (empty DB) it seeds intents/phrases from
src/intent/training_data.json and responses from
src/core/response_handler.INTENT_RESPONSES.
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Resolve project root (robot_voice/) two levels up from this file
# ---------------------------------------------------------------------------
_HERE = Path(__file__).resolve().parent          # src/web_trainer/
_SRC  = _HERE.parent                             # src/
_ROOT = _SRC.parent                              # robot_voice/

DEFAULT_DB_PATH = str(_ROOT / "data" / "trainer.db")
DEFAULT_TRAINING_JSON = str(_SRC / "intent" / "training_data.json")

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------
_SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS intents (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    name              TEXT UNIQUE NOT NULL,
    fallback_response TEXT DEFAULT '',
    random_response   INTEGER DEFAULT 1,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS phrases (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    intent_id  INTEGER NOT NULL REFERENCES intents(id) ON DELETE CASCADE,
    text       TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS responses (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    intent_id  INTEGER NOT NULL REFERENCES intents(id) ON DELETE CASCADE,
    text       TEXT NOT NULL,
    sort_order INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS training_logs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at    TIMESTAMP,
    finished_at   TIMESTAMP,
    epochs        INTEGER,
    accuracy      REAL,
    total_samples INTEGER,
    loss_history  TEXT,
    status        TEXT DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT
);
"""


class TrainerDB:
    """All DB interactions for the web trainer (thread-safe via check_same_thread=False)."""

    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path or os.environ.get("TRAINER_DB_PATH", DEFAULT_DB_PATH)
        # Ensure parent directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()
        self._seed_if_empty()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    @contextmanager
    def _db(self) -> Generator[sqlite3.Connection, None, None]:
        conn = self._connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._db() as conn:
            conn.executescript(_SCHEMA)

    # ------------------------------------------------------------------
    # Seeding
    # ------------------------------------------------------------------

    def _seed_if_empty(self) -> None:
        with self._db() as conn:
            row = conn.execute("SELECT COUNT(*) FROM intents").fetchone()
            if row[0] > 0:
                return

        logger.info("Empty trainer.db — seeding from training_data.json ...")
        self._seed_from_json()

    def _seed_from_json(self) -> None:
        """Import training_data.json phrases and INTENT_RESPONSES responses."""
        json_path = Path(DEFAULT_TRAINING_JSON)
        if not json_path.exists():
            logger.warning("training_data.json not found at %s; skipping seed.", json_path)
            return

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Load response pools from response_handler
        try:
            from src.core.response_handler import INTENT_RESPONSES
        except ImportError:
            try:
                import sys
                sys.path.insert(0, str(_ROOT))
                from src.core.response_handler import INTENT_RESPONSES  # type: ignore
            except ImportError:
                INTENT_RESPONSES = {}
                logger.warning("Could not import INTENT_RESPONSES; responses will be empty.")

        with self._db() as conn:
            for intent_obj in data.get("intents", []):
                name = intent_obj["name"]
                conn.execute(
                    "INSERT OR IGNORE INTO intents (name) VALUES (?)", (name,)
                )
                row = conn.execute(
                    "SELECT id FROM intents WHERE name=?", (name,)
                ).fetchone()
                intent_id = row["id"]

                for phrase in intent_obj.get("utterances", []):
                    conn.execute(
                        "INSERT INTO phrases (intent_id, text) VALUES (?, ?)",
                        (intent_id, phrase),
                    )

                for i, resp in enumerate(INTENT_RESPONSES.get(name, [])):
                    conn.execute(
                        "INSERT INTO responses (intent_id, text, sort_order) VALUES (?, ?, ?)",
                        (intent_id, resp, i),
                    )

        logger.info("Seeding complete.")

    # ------------------------------------------------------------------
    # Intents
    # ------------------------------------------------------------------

    def list_intents(self) -> list[dict[str, Any]]:
        with self._db() as conn:
            rows = conn.execute("""
                SELECT i.id, i.name, i.fallback_response, i.random_response, i.created_at,
                       COUNT(DISTINCT p.id) AS phrase_count,
                       COUNT(DISTINCT r.id) AS response_count
                FROM intents i
                LEFT JOIN phrases p ON p.intent_id = i.id
                LEFT JOIN responses r ON r.intent_id = i.id
                GROUP BY i.id
                ORDER BY i.name
            """).fetchall()
        return [dict(r) for r in rows]

    def get_intent(self, intent_id: int) -> dict[str, Any] | None:
        with self._db() as conn:
            row = conn.execute(
                "SELECT * FROM intents WHERE id=?", (intent_id,)
            ).fetchone()
            if not row:
                return None
            result = dict(row)
            result["phrases"] = [
                dict(r) for r in conn.execute(
                    "SELECT * FROM phrases WHERE intent_id=? ORDER BY id", (intent_id,)
                ).fetchall()
            ]
            result["responses"] = [
                dict(r) for r in conn.execute(
                    "SELECT * FROM responses WHERE intent_id=? ORDER BY sort_order, id",
                    (intent_id,)
                ).fetchall()
            ]
        return result

    def get_intent_by_name(self, name: str) -> dict[str, Any] | None:
        with self._db() as conn:
            row = conn.execute(
                "SELECT id FROM intents WHERE name=?", (name,)
            ).fetchone()
        if not row:
            return None
        return self.get_intent(row["id"])

    def create_intent(self, name: str) -> dict[str, Any]:
        with self._db() as conn:
            conn.execute("INSERT INTO intents (name) VALUES (?)", (name,))
            row = conn.execute(
                "SELECT id FROM intents WHERE name=?", (name,)
            ).fetchone()
        return self.get_intent(row["id"])  # type: ignore[return-value]

    def update_intent(
        self,
        intent_id: int,
        name: str | None = None,
        fallback_response: str | None = None,
        random_response: int | None = None,
    ) -> dict[str, Any] | None:
        updates: list[str] = []
        params: list[Any] = []
        if name is not None:
            updates.append("name=?")
            params.append(name)
        if fallback_response is not None:
            updates.append("fallback_response=?")
            params.append(fallback_response)
        if random_response is not None:
            updates.append("random_response=?")
            params.append(int(random_response))
        if not updates:
            return self.get_intent(intent_id)
        params.append(intent_id)
        with self._db() as conn:
            conn.execute(
                f"UPDATE intents SET {', '.join(updates)} WHERE id=?", params
            )
        return self.get_intent(intent_id)

    def delete_intent(self, intent_id: int) -> bool:
        with self._db() as conn:
            cur = conn.execute("DELETE FROM intents WHERE id=?", (intent_id,))
        return cur.rowcount > 0

    # ------------------------------------------------------------------
    # Phrases
    # ------------------------------------------------------------------

    def add_phrase(self, intent_id: int, text: str) -> dict[str, Any]:
        with self._db() as conn:
            conn.execute(
                "INSERT INTO phrases (intent_id, text) VALUES (?, ?)", (intent_id, text)
            )
            row = conn.execute(
                "SELECT * FROM phrases WHERE intent_id=? ORDER BY id DESC LIMIT 1",
                (intent_id,),
            ).fetchone()
        return dict(row)

    def delete_phrase(self, phrase_id: int) -> bool:
        with self._db() as conn:
            cur = conn.execute("DELETE FROM phrases WHERE id=?", (phrase_id,))
        return cur.rowcount > 0

    # ------------------------------------------------------------------
    # Responses
    # ------------------------------------------------------------------

    def add_response(self, intent_id: int, text: str) -> dict[str, Any]:
        with self._db() as conn:
            conn.execute(
                "INSERT INTO responses (intent_id, text) VALUES (?, ?)", (intent_id, text)
            )
            row = conn.execute(
                "SELECT * FROM responses WHERE intent_id=? ORDER BY id DESC LIMIT 1",
                (intent_id,),
            ).fetchone()
        return dict(row)

    def delete_response(self, response_id: int) -> bool:
        with self._db() as conn:
            cur = conn.execute("DELETE FROM responses WHERE id=?", (response_id,))
        return cur.rowcount > 0

    # ------------------------------------------------------------------
    # Training logs
    # ------------------------------------------------------------------

    def create_log(self, epochs: int) -> int:
        with self._db() as conn:
            cur = conn.execute(
                "INSERT INTO training_logs (started_at, epochs, status) "
                "VALUES (datetime('now'), ?, 'running')",
                (epochs,),
            )
        return cur.lastrowid  # type: ignore[return-value]

    def update_log(
        self,
        log_id: int,
        status: str,
        accuracy: float | None = None,
        total_samples: int | None = None,
        loss_history: str | None = None,
    ) -> None:
        updates = ["status=?", "finished_at=datetime('now')"]
        params: list[Any] = [status]
        if accuracy is not None:
            updates.append("accuracy=?")
            params.append(accuracy)
        if total_samples is not None:
            updates.append("total_samples=?")
            params.append(total_samples)
        if loss_history is not None:
            updates.append("loss_history=?")
            params.append(loss_history)
        params.append(log_id)
        with self._db() as conn:
            conn.execute(
                f"UPDATE training_logs SET {', '.join(updates)} WHERE id=?", params
            )

    def get_logs(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._db() as conn:
            rows = conn.execute(
                "SELECT * FROM training_logs ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    def get_log(self, log_id: int) -> dict[str, Any] | None:
        with self._db() as conn:
            row = conn.execute(
                "SELECT * FROM training_logs WHERE id=?", (log_id,)
            ).fetchone()
        return dict(row) if row else None

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------

    def get_setting(self, key: str, default: str = "") -> str:
        with self._db() as conn:
            row = conn.execute(
                "SELECT value FROM settings WHERE key=?", (key,)
            ).fetchone()
        return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        with self._db() as conn:
            conn.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, value),
            )

    # ------------------------------------------------------------------
    # Runtime read used by ResponseHandler (pipeline side)
    # ------------------------------------------------------------------

    def all_responses(self) -> dict[str, list[str]]:
        """Return {intent_name: [response_text, ...]} in one query.

        Read by ResponseHandler at startup so live edits in the web trainer
        propagate to the pipeline after a restart (or /api/reload).
        """
        with self._db() as conn:
            rows = conn.execute(
                """
                SELECT i.name AS intent_name, r.text AS response_text
                FROM intents i
                LEFT JOIN responses r ON r.intent_id = i.id
                ORDER BY i.name, r.sort_order, r.id
                """
            ).fetchall()
        out: dict[str, list[str]] = {}
        for row in rows:
            name = row["intent_name"]
            text = row["response_text"]
            bucket = out.setdefault(name, [])
            if text:  # LEFT JOIN can produce NULLs for intents with no responses
                bucket.append(text)
        return out

    # ------------------------------------------------------------------
    # Export (for training + backup)
    # ------------------------------------------------------------------

    def export_training_json(self) -> dict[str, Any]:
        """Export all intents/phrases in the same format as training_data.json."""
        intents = self.list_intents()
        result: list[dict[str, Any]] = []
        for intent in intents:
            detail = self.get_intent(intent["id"])
            if detail is None:
                continue
            result.append({
                "name": detail["name"],
                "utterances": [p["text"] for p in detail["phrases"]],
            })
        return {
            "version": "1.2",
            "description": "Exported by Web Trainer",
            "intents": result,
        }

    def import_training_json(self, data: dict[str, Any]) -> int:
        """Import from backup JSON; merges (does not wipe) existing data. Returns count."""
        count = 0
        for intent_obj in data.get("intents", []):
            name = intent_obj.get("name", "").strip()
            if not name:
                continue
            existing = self.get_intent_by_name(name)
            if existing is None:
                self.create_intent(name)
                existing = self.get_intent_by_name(name)
            if existing is None:
                continue
            intent_id = existing["id"]
            existing_phrases = {p["text"] for p in existing["phrases"]}
            for utt in intent_obj.get("utterances", []):
                if utt not in existing_phrases:
                    self.add_phrase(intent_id, utt)
                    count += 1
        return count
