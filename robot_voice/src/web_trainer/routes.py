"""All page + API routes for the Web Trainer Flask app."""
from __future__ import annotations

import io
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

from flask import (
    Blueprint,
    Response,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)

from src.web_trainer.models import TrainerDB

logger = logging.getLogger(__name__)

bp = Blueprint("trainer", __name__)

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent.parent  # robot_voice/

# In-memory store for active training jobs  {job_id: {...}}
_JOBS: dict[str, dict[str, Any]] = {}
_JOBS_LOCK = threading.Lock()


# ---------------------------------------------------------------------------
# DB helper
# ---------------------------------------------------------------------------

def _db() -> TrainerDB:
    db_path = current_app.config.get("TRAINER_DB_PATH")
    return TrainerDB(db_path=db_path)


# ---------------------------------------------------------------------------
# Page routes
# ---------------------------------------------------------------------------

@bp.route("/")
def dashboard():
    intents = _db().list_intents()
    return render_template("dashboard.html", intents=intents, active="dashboard")


@bp.route("/intents/<int:intent_id>")
def intent_edit(intent_id: int):
    db = _db()
    intent = db.get_intent(intent_id)
    if intent is None:
        return redirect(url_for("trainer.dashboard"))
    intents = db.list_intents()
    return render_template(
        "intent_edit.html", intent=intent, intents=intents, active="dashboard"
    )


@bp.route("/training")
def training():
    db = _db()
    intents = db.list_intents()
    model_path = db.get_setting(
        "model_path",
        str(_ROOT / "models" / "hotel_reception_intent.bin"),
    )
    return render_template(
        "training.html",
        intents=intents,
        model_path=model_path,
        active="training",
    )


@bp.route("/testing")
def testing():
    db = _db()
    intents = db.list_intents()
    return render_template("test.html", intents=intents, active="testing")


@bp.route("/settings")
def settings():
    db = _db()
    intents = db.list_intents()
    model_path = db.get_setting(
        "model_path",
        str(_ROOT / "models" / "hotel_reception_intent.bin"),
    )
    db_path_val = db.db_path
    return render_template(
        "settings.html",
        intents=intents,
        model_path=model_path,
        db_path=db_path_val,
        active="settings",
    )


@bp.route("/logs")
def logs():
    db = _db()
    intents = db.list_intents()
    training_logs = db.get_logs(limit=100)
    return render_template(
        "logs.html", intents=intents, training_logs=training_logs, active="logs"
    )


# ---------------------------------------------------------------------------
# API — Intents
# ---------------------------------------------------------------------------

@bp.route("/api/intents", methods=["GET"])
def api_list_intents():
    return jsonify(_db().list_intents())


@bp.route("/api/intents", methods=["POST"])
def api_create_intent():
    data = request.get_json(force=True)
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400
    try:
        intent = _db().create_intent(name)
        return jsonify(intent), 201
    except Exception as exc:
        return jsonify({"error": str(exc)}), 409


@bp.route("/api/intents/<int:intent_id>", methods=["GET"])
def api_get_intent(intent_id: int):
    intent = _db().get_intent(intent_id)
    if intent is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(intent)


@bp.route("/api/intents/<int:intent_id>", methods=["PUT"])
def api_update_intent(intent_id: int):
    data = request.get_json(force=True)
    intent = _db().update_intent(
        intent_id,
        name=data.get("name"),
        fallback_response=data.get("fallback_response"),
        random_response=data.get("random_response"),
    )
    if intent is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(intent)


@bp.route("/api/intents/<int:intent_id>", methods=["DELETE"])
def api_delete_intent(intent_id: int):
    ok = _db().delete_intent(intent_id)
    if not ok:
        return jsonify({"error": "not found"}), 404
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# API — Phrases
# ---------------------------------------------------------------------------

@bp.route("/api/intents/<int:intent_id>/phrases", methods=["POST"])
def api_add_phrase(intent_id: int):
    data = request.get_json(force=True)
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "text is required"}), 400
    phrase = _db().add_phrase(intent_id, text)
    return jsonify(phrase), 201


@bp.route("/api/intents/<int:intent_id>/phrases/<int:phrase_id>", methods=["DELETE"])
def api_delete_phrase(intent_id: int, phrase_id: int):
    ok = _db().delete_phrase(phrase_id)
    if not ok:
        return jsonify({"error": "not found"}), 404
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# API — Responses
# ---------------------------------------------------------------------------

@bp.route("/api/intents/<int:intent_id>/responses", methods=["POST"])
def api_add_response(intent_id: int):
    data = request.get_json(force=True)
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "text is required"}), 400
    resp = _db().add_response(intent_id, text)
    return jsonify(resp), 201


@bp.route("/api/intents/<int:intent_id>/responses/<int:response_id>", methods=["DELETE"])
def api_delete_response(intent_id: int, response_id: int):
    ok = _db().delete_response(response_id)
    if not ok:
        return jsonify({"error": "not found"}), 404
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# API — Training
# ---------------------------------------------------------------------------

def _run_training_job(job_id: str, epochs: int, lr: float, word_ngrams: int,
                      min_count: int, thread: int, db: TrainerDB) -> None:
    """Background thread: exports JSON, spawns train.py, parses output."""
    log_file = Path(tempfile.gettempdir()) / f"train_{job_id}.log"
    log_id = db.create_log(epochs=epochs)

    try:
        # Export current trainer.db to training_data.json
        training_json = db.export_training_json()
        json_path = _ROOT / "src" / "intent" / "training_data.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(training_json, f, indent=2, ensure_ascii=False)

        env = os.environ.copy()
        env.update({
            "TRAIN_EPOCHS": str(epochs),
            "TRAIN_LR": str(lr),
            "TRAIN_WORD_NGRAMS": str(word_ngrams),
            "TRAIN_MIN_COUNT": str(min_count),
            "TRAIN_THREAD": str(thread),
        })

        cmd = [sys.executable, "-m", "src.intent.train"]
        with open(log_file, "w", encoding="utf-8") as lf:
            proc = subprocess.Popen(
                cmd,
                cwd=str(_ROOT),
                stdout=lf,
                stderr=subprocess.STDOUT,
                env=env,
            )

        loss_history: list[str] = []
        accuracy: float = 0.0
        total_samples: int = 0

        # Poll for completion
        while proc.poll() is None:
            with _JOBS_LOCK:
                job = _JOBS.get(job_id, {})
                if job.get("cancel"):
                    proc.terminate()
                    break
            _parse_log(log_file, job_id, epochs, loss_history)
            time.sleep(0.5)

        # Final parse
        _parse_log(log_file, job_id, epochs, loss_history)

        # Read accuracy from log
        if log_file.exists():
            content = log_file.read_text(encoding="utf-8", errors="ignore")
            acc_match = re.search(r"[Aa]ccuracy[:\s]+([0-9.]+)", content)
            if acc_match:
                accuracy = float(acc_match.group(1))
            sample_match = re.search(r"[Tt]otal\s+samples?[:\s]+(\d+)", content)
            if sample_match:
                total_samples = int(sample_match.group(1))

        exit_code = proc.returncode or 0
        status = "completed" if exit_code == 0 else "failed"

        with _JOBS_LOCK:
            _JOBS[job_id]["status"] = status
            _JOBS[job_id]["progress"] = 100
            _JOBS[job_id]["accuracy"] = accuracy
            _JOBS[job_id]["total_samples"] = total_samples

        db.update_log(
            log_id,
            status=status,
            accuracy=accuracy,
            total_samples=total_samples,
            loss_history=json.dumps(loss_history),
        )

    except Exception as exc:
        logger.exception("Training job %s crashed", job_id)
        with _JOBS_LOCK:
            _JOBS[job_id]["status"] = "failed"
            _JOBS[job_id]["error"] = str(exc)
        db.update_log(log_id, status="failed")


def _parse_log(
    log_file: Path, job_id: str, total_epochs: int, loss_history: list[str]
) -> None:
    if not log_file.exists():
        return
    content = log_file.read_text(encoding="utf-8", errors="ignore")
    # Match "Epoch X/Y - Loss: Z" OR "Progress: X%"
    epoch_matches = re.findall(r"[Ee]poch\s+(\d+)/(\d+)\s*[-–]\s*[Ll]oss:\s*([0-9.]+)", content)
    if epoch_matches:
        last = epoch_matches[-1]
        done, total, loss = int(last[0]), int(last[1]), last[2]
        progress = int(done / max(total, 1) * 100)
        with _JOBS_LOCK:
            _JOBS[job_id]["epochs_done"] = done
            _JOBS[job_id]["loss"] = float(loss)
            _JOBS[job_id]["progress"] = progress
        # Append new losses
        for m in epoch_matches:
            entry = f"Epoch {m[0]}/{m[1]} - Loss: {m[2]}"
            if entry not in loss_history:
                loss_history.append(entry)


@bp.route("/api/train", methods=["POST"])
def api_train():
    data = request.get_json(force=True) or {}
    epochs = int(data.get("epochs", 25))
    lr = float(data.get("lr", 0.1))
    word_ngrams = int(data.get("word_ngrams", 2))
    min_count = int(data.get("min_count", 1))
    thread = int(data.get("thread", 4))

    import uuid
    job_id = str(uuid.uuid4())[:8]
    db = _db()

    with _JOBS_LOCK:
        _JOBS[job_id] = {
            "status": "running",
            "progress": 0,
            "epochs_done": 0,
            "loss": None,
            "accuracy": None,
            "total_samples": None,
            "cancel": False,
        }

    t = threading.Thread(
        target=_run_training_job,
        args=(job_id, epochs, lr, word_ngrams, min_count, thread, db),
        daemon=True,
        name=f"TrainJob-{job_id}",
    )
    t.start()

    return jsonify({"job_id": job_id}), 202


@bp.route("/api/train/status/<job_id>")
def api_train_status(job_id: str):
    with _JOBS_LOCK:
        job = _JOBS.get(job_id)
    if job is None:
        return jsonify({"error": "job not found"}), 404
    return jsonify(job)


# ---------------------------------------------------------------------------
# API — Model info
# ---------------------------------------------------------------------------

@bp.route("/api/model/info")
def api_model_info():
    db = _db()
    model_path_str = db.get_setting(
        "model_path",
        str(_ROOT / "models" / "hotel_reception_intent.bin"),
    )
    model_path = Path(model_path_str)
    info: dict[str, Any] = {
        "model_path": model_path_str,
        "exists": model_path.exists(),
    }
    if model_path.exists():
        stat = model_path.stat()
        import datetime
        info["trained_at"] = datetime.datetime.fromtimestamp(stat.st_mtime).isoformat()
        info["size_bytes"] = stat.st_size
    # Pull latest successful log
    logs = db.get_logs(limit=1)
    if logs:
        latest = logs[0]
        info["accuracy"] = latest.get("accuracy")
        info["epochs"] = latest.get("epochs")
        info["total_samples"] = latest.get("total_samples")
        info["last_trained"] = latest.get("finished_at")
        info["status"] = latest.get("status")
    return jsonify(info)


# ---------------------------------------------------------------------------
# API — Hot-reload
# ---------------------------------------------------------------------------

@bp.route("/api/reload", methods=["POST"])
def api_reload():
    db = _db()
    model_path_str = db.get_setting(
        "model_path",
        str(_ROOT / "models" / "hotel_reception_intent.bin"),
    )
    model_path = Path(model_path_str)
    if not model_path.exists():
        return jsonify({"error": "model file not found"}), 404
    # Touch the file to trigger mtime-based hot-reload in classifier.py
    model_path.touch()
    return jsonify({"ok": True, "model_path": model_path_str})


# ---------------------------------------------------------------------------
# API — System info
# ---------------------------------------------------------------------------

@bp.route("/api/system")
def api_system():
    import sys as _sys
    import platform
    info: dict[str, Any] = {
        "python": platform.python_version(),
        "platform": platform.system(),
    }
    # fasttext version
    try:
        import fasttext as _ft  # type: ignore
        info["fasttext"] = getattr(_ft, "__version__", "0.9.x")
    except ImportError:
        info["fasttext"] = "not installed"
    # RAM via psutil (optional)
    try:
        import psutil
        vm = psutil.virtual_memory()
        info["ram_used"] = f"{vm.used/1024**3:.1f} GB"
        info["ram_total"] = f"{vm.total/1024**3:.1f} GB"
        info["ram_pct"] = vm.percent
    except ImportError:
        try:
            import subprocess
            result = subprocess.run(
                ["free", "-m"], capture_output=True, text=True, timeout=2
            )
            lines = result.stdout.strip().splitlines()
            if len(lines) >= 2:
                parts = lines[1].split()
                total_mb = int(parts[1])
                used_mb = int(parts[2])
                info["ram_used"] = f"{used_mb/1024:.1f} GB"
                info["ram_total"] = f"{total_mb/1024:.1f} GB"
                info["ram_pct"] = round(used_mb/total_mb*100, 1)
        except Exception:
            info["ram_used"] = "N/A"
            info["ram_total"] = "N/A"
            info["ram_pct"] = 0
    return jsonify(info)


# ---------------------------------------------------------------------------
# API — Backup / Restore
# ---------------------------------------------------------------------------

@bp.route("/api/backup")
def api_backup():
    db = _db()
    data = db.export_training_json()
    buf = io.BytesIO(json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8"))
    buf.seek(0)
    return send_file(
        buf,
        mimetype="application/json",
        as_attachment=True,
        download_name="training_data.json",
    )


@bp.route("/api/restore", methods=["POST"])
def api_restore():
    if "file" not in request.files:
        return jsonify({"error": "no file uploaded"}), 400
    f = request.files["file"]
    try:
        data = json.load(f)
    except Exception as exc:
        return jsonify({"error": f"invalid JSON: {exc}"}), 400
    db = _db()
    count = db.import_training_json(data)
    return jsonify({"ok": True, "imported_phrases": count})


# ---------------------------------------------------------------------------
# API — Logs
# ---------------------------------------------------------------------------

@bp.route("/api/logs")
def api_logs():
    limit = int(request.args.get("limit", 100))
    return jsonify(_db().get_logs(limit=limit))


# ---------------------------------------------------------------------------
# API — Settings
# ---------------------------------------------------------------------------

@bp.route("/api/settings", methods=["GET"])
def api_get_settings():
    db = _db()
    return jsonify({
        "model_path": db.get_setting(
            "model_path",
            str(_ROOT / "models" / "hotel_reception_intent.bin"),
        ),
        "db_path": db.db_path,
    })


@bp.route("/api/settings", methods=["POST"])
def api_save_settings():
    data = request.get_json(force=True) or {}
    db = _db()
    if "model_path" in data:
        db.set_setting("model_path", data["model_path"])
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# API — Testing
# ---------------------------------------------------------------------------

def _get_classifier():
    """Lazily load/cache the IntentClassifier on the Flask app object."""
    app = current_app._get_current_object()  # type: ignore[attr-defined]
    if not hasattr(app, "_intent_classifier"):
        db = _db()
        model_path = db.get_setting(
            "model_path",
            str(_ROOT / "models" / "hotel_reception_intent.bin"),
        )
        try:
            from src.intent.classifier import IntentClassifier
            app._intent_classifier = IntentClassifier(model_path=model_path, watch=True)
        except Exception as exc:
            logger.warning("Could not load classifier: %s", exc)
            app._intent_classifier = None
    return app._intent_classifier


@bp.route("/api/test/single", methods=["POST"])
def api_test_single():
    data = request.get_json(force=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "text is required"}), 400
    clf = _get_classifier()
    if clf is None:
        return jsonify({"error": "Model not loaded. Train a model first."}), 503
    result = clf.predict(text)
    return jsonify({
        "text": text,
        "intent": result["intent"],
        "confidence": round(result["confidence"], 4),
        "all_scores": {k: round(v, 4) for k, v in result.get("all_scores", {}).items()},
    })


@bp.route("/api/test/batch", methods=["POST"])
def api_test_batch():
    data = request.get_json(force=True) or {}
    texts = data.get("texts", [])
    if not texts:
        return jsonify({"error": "texts list is required"}), 400
    clf = _get_classifier()
    if clf is None:
        return jsonify({"error": "Model not loaded. Train a model first."}), 503
    results = []
    for text in texts:
        t = (text or "").strip()
        if not t:
            continue
        r = clf.predict(t)
        results.append({
            "text": t,
            "intent": r["intent"],
            "confidence": round(r["confidence"], 4),
        })
    return jsonify(results)
