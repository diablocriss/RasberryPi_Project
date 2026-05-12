#!/usr/bin/env bash
# update-manifest.sh — regenerate skills/manifest.json by scanning skills/*/SKILL.md
#
# Usage:
#   ./scripts/update-manifest.sh

set -euo pipefail

SKILLS_DIR="skills"
MANIFEST="${SKILLS_DIR}/manifest.json"

if [[ ! -d "$SKILLS_DIR" ]]; then
    echo "No skills/ directory found. Creating it..."
    mkdir -p "$SKILLS_DIR"
fi

# Collect entries by scanning each SKILL.md
entries=()

for skill_file in "$SKILLS_DIR"/*/SKILL.md; do
    [[ -f "$skill_file" ]] || continue

    # Extract skill name from directory name
    skill_dir=$(dirname "$skill_file")
    skill_name=$(basename "$skill_dir")

    # Extract description: first non-empty, non-header line after "## Purpose"
    description=$(awk '
        /^## Purpose/ { found=1; next }
        found && /^##/ { exit }
        found && /^[^[:space:]]/ && !/^>/ { print; exit }
    ' "$skill_file" | sed 's/^[[:space:]]*//' | head -1)

    if [[ -z "$description" ]]; then
        # Fallback: first non-empty line after the title
        description=$(grep -v '^#' "$skill_file" | grep -v '^---' | grep -v '^>' | \
                      grep -v '^[[:space:]]*$' | head -1 | sed 's/^[[:space:]]*//')
    fi

    if [[ -z "$description" ]]; then
        description="No description."
    fi

    entries+=("$(printf '    {"name": "%s", "description": "%s", "path": "%s"}' \
        "$skill_name" \
        "$(echo "$description" | sed 's/"/\\"/g')" \
        "$skill_file")")
done

# Write manifest
{
    echo "{"
    echo '  "version": 1,'
    echo '  "skills": ['
    for i in "${!entries[@]}"; do
        if [[ $i -lt $((${#entries[@]} - 1)) ]]; then
            echo "${entries[$i]},"
        else
            echo "${entries[$i]}"
        fi
    done
    echo '  ]'
    echo "}"
} > "$MANIFEST"

echo "Updated $MANIFEST with ${#entries[@]} skill(s):"
for skill_file in "$SKILLS_DIR"/*/SKILL.md; do
    [[ -f "$skill_file" ]] || continue
    skill_name=$(basename "$(dirname "$skill_file")")
    echo "  - $skill_name"
done
