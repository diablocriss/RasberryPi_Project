# Ollama Gemma3 Migration

This migration adds an Ollama-backed command parser for Raspberry Pi 4 while keeping the fast rule/regex path. Common commands should resolve locally in under 10 ms. Ollama is used only for uncommon phrases.

## Files Added

- `src/core/ollama_pipeline.py`: rule-first pipeline with async Ollama fallback.
- `Modelfile`: optimized `robot-command` model definition.
- `scripts/install_ollama_gemma3.sh`: install Ollama, pull Gemma3 Q4, create model, install systemd service.
- `scripts/migrate_to_ollama_gemma3.sh`: backup, install, test, and rollback helper.
- `systemd/ollama-robot.service`: boot service for `ollama serve`.
- `tests/test_ollama_pipeline.py`: fast-path and optional live Ollama validation.

## Install On Raspberry Pi

```bash
cd /home/phuong/robot_voice
chmod +x scripts/install_ollama_gemma3.sh scripts/migrate_to_ollama_gemma3.sh
./scripts/install_ollama_gemma3.sh
```

The installer:

1. Installs Ollama if missing.
2. Installs `aiohttp` into `.venv` when present.
3. Installs and enables `ollama-robot.service`.
4. Pulls `antconsales/antonio-gemma3-smart-q4`.
5. Creates the local `robot-command` model from `Modelfile`.

## Full Migration With Backup

```bash
cd /home/phuong/robot_voice
./scripts/migrate_to_ollama_gemma3.sh
```

Backups are written to:

```text
backups/llama_cpp_YYYYMMDD_HHMMSS/
```

Rollback:

```bash
./scripts/migrate_to_ollama_gemma3.sh --rollback backups/llama_cpp_YYYYMMDD_HHMMSS
```

## Test

Fast-path rules only:

```bash
.venv/bin/python -m pytest tests/test_ollama_pipeline.py -q
```

Live Ollama fallback:

```bash
.venv/bin/python tests/test_ollama_pipeline.py --live
```

Expected targets:

- First cold Ollama command: under 5 seconds.
- Warm Ollama fallback: under 4 seconds.
- Rule/cache hits: under 0.01 seconds.
- Accuracy: at least 10/11 command cases.

## Runtime Notes

The pipeline order is:

```text
exact rules -> regex rules -> LRU cache -> Ollama API -> STOP fallback
```

If Ollama is down, restarting, or times out, the robot continues in degraded rule-only mode and returns a safe fallback for unmatched commands.

Check service state:

```bash
systemctl status ollama-robot.service
curl http://127.0.0.1:11434/api/tags
ollama list
```

Memory check:

```bash
ps -o pid,rss,cmd -C ollama
free -h
```
