#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_ROOT="$PROJECT_DIR/backups"
STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="$BACKUP_ROOT/llama_cpp_$STAMP"
SERVICE_NAME="${SERVICE_NAME:-ollama-robot.service}"

log() {
  printf '[ollama-migrate] %s\n' "$*"
}

backup_current() {
  mkdir -p "$BACKUP_DIR"
  log "Backing up current llama.cpp-related files to $BACKUP_DIR"
  cp -a "$PROJECT_DIR/src/core/optimized_pipeline.py" "$BACKUP_DIR/" 2>/dev/null || true
  cp -a "$PROJECT_DIR/requirements-pi.txt" "$BACKUP_DIR/" 2>/dev/null || true
  cp -a "$PROJECT_DIR/requirements.txt" "$BACKUP_DIR/" 2>/dev/null || true
  if [ -d "$PROJECT_DIR/models" ]; then
    find "$PROJECT_DIR/models" -maxdepth 1 -type f -name '*.gguf' -exec cp -a {} "$BACKUP_DIR/" \; 2>/dev/null || true
  fi
  printf '%s\n' "$BACKUP_DIR" > "$BACKUP_ROOT/latest_ollama_migration_backup.txt"
}

rollback() {
  local backup="${1:-}"
  if [ -z "$backup" ] && [ -f "$BACKUP_ROOT/latest_ollama_migration_backup.txt" ]; then
    backup="$(cat "$BACKUP_ROOT/latest_ollama_migration_backup.txt")"
  fi
  if [ -z "$backup" ] || [ ! -d "$backup" ]; then
    log "No backup directory found. Pass one explicitly: $0 --rollback /path/to/backup"
    exit 1
  fi

  log "Rolling back from $backup"
  cp -a "$backup/optimized_pipeline.py" "$PROJECT_DIR/src/core/optimized_pipeline.py" 2>/dev/null || true
  cp -a "$backup/requirements-pi.txt" "$PROJECT_DIR/requirements-pi.txt" 2>/dev/null || true
  cp -a "$backup/requirements.txt" "$PROJECT_DIR/requirements.txt" 2>/dev/null || true
  sudo systemctl disable --now "$SERVICE_NAME" 2>/dev/null || true
  if systemctl list-unit-files ollama.service >/dev/null 2>&1; then
    sudo systemctl enable --now ollama.service || true
  fi
  log "Rollback complete."
}

test_pipeline() {
  log "Testing robot-command model via Python pipeline..."
  if [ -x "$PROJECT_DIR/.venv/bin/python" ]; then
    "$PROJECT_DIR/.venv/bin/python" "$PROJECT_DIR/tests/test_ollama_pipeline.py" --live
  else
    python3 "$PROJECT_DIR/tests/test_ollama_pipeline.py" --live
  fi
}

main() {
  if [ "${1:-}" = "--rollback" ]; then
    rollback "${2:-}"
    exit 0
  fi

  backup_current
  "$PROJECT_DIR/scripts/install_ollama_gemma3.sh"
  test_pipeline
  log "Migration complete. Backup: $BACKUP_DIR"
  log "Rollback with: $0 --rollback $BACKUP_DIR"
}

main "$@"
