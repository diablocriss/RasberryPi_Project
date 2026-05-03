#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODEL_SOURCE="${MODEL_SOURCE:-antconsales/antonio-gemma3-smart-q4}"
MODEL_NAME="${MODEL_NAME:-robot-command}"
SERVICE_NAME="${SERVICE_NAME:-ollama-robot.service}"
SERVICE_USER="${SERVICE_USER:-$(id -un)}"
SERVICE_GROUP="${SERVICE_GROUP:-$(id -gn)}"

log() {
  printf '[ollama-install] %s\n' "$*"
}

require_sudo() {
  if ! sudo -n true 2>/dev/null; then
    log "sudo access is required for systemd setup."
    sudo true
  fi
}

install_ollama() {
  if command -v ollama >/dev/null 2>&1; then
    log "Ollama already installed: $(command -v ollama)"
    return
  fi
  log "Installing Ollama..."
  curl -fsSL https://ollama.com/install.sh | sh
}

install_python_deps() {
  if [ -x "$PROJECT_DIR/.venv/bin/python" ]; then
    log "Installing aiohttp into project venv..."
    "$PROJECT_DIR/.venv/bin/python" -m pip install "aiohttp>=3.9,<4.0"
  else
    log "No .venv found; skipping Python dependency install."
  fi
}

install_service() {
  require_sudo
  local template="$PROJECT_DIR/systemd/$SERVICE_NAME"
  local tmp="/tmp/$SERVICE_NAME"

  sed \
    -e "s/^User=.*/User=$SERVICE_USER/" \
    -e "s/^Group=.*/Group=$SERVICE_GROUP/" \
    "$template" > "$tmp"

  log "Installing systemd service $SERVICE_NAME..."
  sudo install -m 0644 "$tmp" "/etc/systemd/system/$SERVICE_NAME"
  sudo systemctl daemon-reload
  sudo systemctl enable "$SERVICE_NAME"

  if systemctl list-unit-files ollama.service >/dev/null 2>&1; then
    log "Disabling default ollama.service to avoid port conflicts..."
    sudo systemctl disable --now ollama.service || true
  fi

  sudo systemctl restart "$SERVICE_NAME"
}

wait_for_ollama() {
  log "Waiting for Ollama API..."
  for _ in $(seq 1 30); do
    if curl -fsS http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
      log "Ollama API is ready."
      return
    fi
    sleep 1
  done
  log "Ollama API did not become ready in time."
  return 1
}

create_model() {
  log "Pulling $MODEL_SOURCE..."
  ollama pull "$MODEL_SOURCE"

  log "Creating optimized model $MODEL_NAME from Modelfile..."
  ollama create "$MODEL_NAME" -f "$PROJECT_DIR/Modelfile"
}

smoke_test() {
  log "Smoke testing model..."
  local response
  response="$(ollama run "$MODEL_NAME" "go back" || true)"
  printf '%s\n' "$response"
  if ! printf '%s' "$response" | grep -q 'BACKWARD'; then
    log "Smoke test warning: response did not include BACKWARD."
  fi
}

main() {
  install_ollama
  install_python_deps
  install_service
  wait_for_ollama
  create_model
  smoke_test
  log "Done. Test Python pipeline with:"
  log "  cd $PROJECT_DIR && .venv/bin/python tests/test_ollama_pipeline.py --live"
}

main "$@"
