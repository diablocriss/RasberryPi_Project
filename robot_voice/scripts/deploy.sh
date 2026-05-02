#!/usr/bin/env bash
set -euo pipefail

TARGET="${1:-phuong@192.168.1.66:/home/phuong/robot_voice}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

ssh "${TARGET%%:*}" "mkdir -p '${TARGET#*:}'"
scp -r "$ROOT_DIR/src" "$ROOT_DIR/tests" "$ROOT_DIR/scripts" "$ROOT_DIR/configs" "$ROOT_DIR/requirements.txt" "$ROOT_DIR/README.md" "$ROOT_DIR/.env.example" "$TARGET"
ssh "${TARGET%%:*}" "chmod +x '${TARGET#*:}/scripts/'*.sh"