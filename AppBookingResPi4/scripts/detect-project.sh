#!/usr/bin/env bash
# detect-project.sh — detect project type and output build/test/run/lint commands.
#
# Usage:
#   source scripts/detect-project.sh       # sets env vars in caller
#   scripts/detect-project.sh              # prints detected values
#
# Output variables (when sourced):
#   DETECTED_TYPE    project type string
#   DETECTED_BUILD   build command
#   DETECTED_TEST    test command (empty if none)
#   DETECTED_RUN     run command
#   DETECTED_LINT    lint command (empty if none)

set -euo pipefail

DETECTED_TYPE=""
DETECTED_BUILD=""
DETECTED_TEST=""
DETECTED_RUN=""
DETECTED_LINT=""

# ── Detection rules (priority order) ─────────────────────────────────────────

# ESP-IDF
if [[ -f "idf_component.yml" || -f "sdkconfig" || -f "sdkconfig.defaults" ]]; then
    DETECTED_TYPE="esp-idf"
    DETECTED_BUILD="idf.py build"
    DETECTED_TEST="idf.py flash monitor"
    DETECTED_RUN=""
    DETECTED_LINT=""

# Rust
elif [[ -f "Cargo.toml" ]]; then
    DETECTED_TYPE="rust"
    DETECTED_BUILD="cargo build"
    DETECTED_TEST="cargo test"
    DETECTED_RUN="cargo run"
    DETECTED_LINT="cargo clippy"

# Node.js / TypeScript
elif [[ -f "package.json" ]]; then
    DETECTED_TYPE="nodejs"
    local_build=$(python3 -c "import json; d=json.load(open('package.json')); print(d.get('scripts',{}).get('build','npm run build'))" 2>/dev/null || echo "npm run build")
    local_test=$(python3 -c "import json; d=json.load(open('package.json')); print(d.get('scripts',{}).get('test','npm test'))" 2>/dev/null || echo "npm test")
    DETECTED_BUILD="$local_build"
    DETECTED_TEST="$local_test"
    DETECTED_RUN="npm start"
    DETECTED_LINT="npm run lint"

# Python
elif [[ -f "requirements.txt" || -f "pyproject.toml" || -f "setup.py" ]]; then
    DETECTED_TYPE="python"
    DETECTED_BUILD="pip install -r requirements.txt"
    DETECTED_TEST="pytest -x"
    DETECTED_RUN="python main.py"
    DETECTED_LINT="ruff check ."

# Go
elif [[ -f "go.mod" ]]; then
    DETECTED_TYPE="go"
    DETECTED_BUILD="go build ./..."
    DETECTED_TEST="go test ./..."
    DETECTED_RUN="go run ."
    DETECTED_LINT="golangci-lint run"

# C/C++ — AppBookingResPi4 (Makefile + src/*.c)
elif [[ -f "Makefile" && -d "src" ]]; then
    # Check if this is the AppBookingResPi4 pattern
    if ls src/*.c &>/dev/null 2>&1; then
        DETECTED_TYPE="c-make"
        DETECTED_BUILD="make clean && make"
        DETECTED_TEST=""
        DETECTED_RUN="./appbooking -p 8080 -d /tmp/test.db"
        DETECTED_LINT=""
    else
        DETECTED_TYPE="make"
        DETECTED_BUILD="make"
        DETECTED_TEST="make test"
        DETECTED_RUN=""
        DETECTED_LINT=""
    fi

# CMake
elif [[ -f "CMakeLists.txt" ]]; then
    DETECTED_TYPE="cmake"
    DETECTED_BUILD="cmake -B build && cmake --build build"
    DETECTED_TEST="ctest --test-dir build"
    DETECTED_RUN=""
    DETECTED_LINT=""

# Generic Makefile
elif [[ -f "Makefile" || -f "makefile" ]]; then
    DETECTED_TYPE="make"
    DETECTED_BUILD="make"
    DETECTED_TEST="make test"
    DETECTED_RUN=""
    DETECTED_LINT=""

else
    DETECTED_TYPE="unknown"
    DETECTED_BUILD="[BUILD_COMMAND]"
    DETECTED_TEST="[TEST_COMMAND]"
    DETECTED_RUN="[RUN_COMMAND]"
    DETECTED_LINT=""
fi

# ── Output ────────────────────────────────────────────────────────────────────

# If sourced, variables are exported. If run directly, print them.
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "DETECTED_TYPE:  $DETECTED_TYPE"
    echo "DETECTED_BUILD: $DETECTED_BUILD"
    echo "DETECTED_TEST:  $DETECTED_TEST"
    echo "DETECTED_RUN:   $DETECTED_RUN"
    echo "DETECTED_LINT:  $DETECTED_LINT"
fi

export DETECTED_TYPE DETECTED_BUILD DETECTED_TEST DETECTED_RUN DETECTED_LINT
