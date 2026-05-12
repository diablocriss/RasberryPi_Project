#!/usr/bin/env bash
# load_skill.sh — list or print skills from the skills/ directory.
#
# Usage:
#   ./scripts/load_skill.sh list              print all skill names and descriptions
#   ./scripts/load_skill.sh <skill-name>      print the content of that skill's SKILL.md

set -euo pipefail

MANIFEST="skills/manifest.json"
SKILLS_DIR="skills"

if [[ $# -eq 0 ]]; then
    echo "Usage:"
    echo "  $0 list              List all available skills"
    echo "  $0 <skill-name>      Print the content of that skill"
    exit 1
fi

CMD="$1"

# ── list ──────────────────────────────────────────────────────────────────────

if [[ "$CMD" == "list" ]]; then
    if [[ ! -f "$MANIFEST" ]]; then
        echo "No manifest found at $MANIFEST"
        echo "Run ./scripts/update-manifest.sh to generate it."
        exit 1
    fi

    if command -v python3 &>/dev/null; then
        python3 - "$MANIFEST" <<'PY'
import json, sys
data = json.load(open(sys.argv[1]))
for s in data.get("skills", []):
    print(f"  {s['name']:<22} {s['description'][:80]}")
PY
    else
        paste \
            <(grep '"name"' "$MANIFEST" | sed 's/.*"name": *"\([^"]*\)".*/\1/') \
            <(grep '"description"' "$MANIFEST" | sed 's/.*"description": *"\([^"]*\)".*/\1/') \
            | awk -F'\t' '{ printf "  %-22s %s\n", $1, substr($2,1,80) }'
    fi
    exit 0
fi

# ── load <skill-name> ─────────────────────────────────────────────────────────

SKILL_NAME="$CMD"
SKILL_FILE="${SKILLS_DIR}/${SKILL_NAME}/SKILL.md"

if [[ ! -f "$SKILL_FILE" ]]; then
    echo "Skill not found: $SKILL_NAME"
    echo ""
    echo "Available skills:"
    "$0" list
    exit 1
fi

cat "$SKILL_FILE"
