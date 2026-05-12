# CLAUDE.md

This file is loaded automatically by Claude Code. It defines how Claude should
behave in this project and provides essential context about the codebase.

---

## Project overview

**Project:** AppBookingResPi4
**Type:** C / Make (Raspberry Pi 4 embedded)
**Language(s):** C (C11), HTML/CSS/JS (embedded UI)
**Description:** A lightweight HTTP booking-reservation server written in C, designed to run on Raspberry Pi 4 with an embedded web dashboard and SQLite persistence.

---

## Commands

```bash
# Build (native x86_64, WSL2/Ubuntu)
make

# Cross-compile for Raspberry Pi 4 (arm-linux-gnueabihf)
make pi

# Deploy to Pi #1
make deploy

# Deploy to Pi #2
make deploy2

# Clean all artifacts
make clean

# Install native binary to /usr/local/bin
sudo make install

# Run locally
./appbooking -p 8080 -d bookings.db

# Scaffold a new plan
./scripts/plan-executor.sh new <feature-name>

# List all plans and their status
./scripts/plan-executor.sh list

# Show task progress for a plan
./scripts/plan-executor.sh status <plan-folder>

# Print a plan to paste into Copilot
./scripts/plan-executor.sh open <plan-folder>

# Run build + test from config
./scripts/plan-executor.sh test
```

---

## Architecture

```
src/
  main.c        ← CLI entry point, flag parsing, startup
  server.c      ← TCP HTTP server, pthread per connection
  api.c         ← REST route dispatcher and handlers
  booking.c     ← Domain logic (CRUD, validation, conflict detection)
  storage.c     ← SQLite3 persistence layer
  web.c         ← Serves embedded HTML dashboard
  web.h / *.h   ← Header files per module
web/
  index.html    ← Editable dashboard source → compiled to src/index_html.h via xxd
build/
  obj/          ← Native object files
  obj-pi/       ← ARM object files
lib/            ← Static third-party libraries (if any)
scripts/
  install-service.sh  ← Installs systemd service on Pi
  backup-db.sh        ← Timestamped SQLite backup
  plan-executor.sh    ← Plan lifecycle helper
  load_skill.sh       ← Skill listing / printing
  update-manifest.sh  ← Regenerates skills/manifest.json
  detect-project.sh   ← Detects project type and commands
  init.sh             ← One-command setup / upgrade
skills/
  manifest.json       ← Index of all skills (auto-generated)
  <skill>/SKILL.md    ← Domain knowledge for one codebase area
.plans/
  YYYY-MM-DD-<name>/  ← Plan folders: spec.md, tasks.md, tests.md
.planner-executor/
  config.yaml         ← Build/test/run commands for plan-executor.sh
```

**Main data flow:**
1. Client HTTP request → `server.c` (accept, recv)
2. `api_handle()` → route matching → handler
3. Handler calls `booking.c` domain logic → `storage.c` SQLite
4. Response serialised as JSON → write to socket

---

## Key files

| File | Purpose |
|---|---|
| `src/main.c` | Entry point, CLI flags |
| `src/server.c` | TCP server, thread-per-connection |
| `src/api.c` | REST router and handlers |
| `src/booking.c` | Booking CRUD and conflict validation |
| `src/storage.c` | SQLite3 prepared statements |
| `src/web.c` | Serves embedded `index_html` byte array |
| `web/index.html` | Dashboard source — never edit `src/index_html.h` directly |
| `Makefile` | Native + cross-compile + deploy targets |

---

## Coding conventions

- C11 with `-Wall -Wextra -O2 -D_GNU_SOURCE`
- No external JSON library — parse with `strstr`/`sscanf`
- All timestamps are Unix seconds (int64_t UTC)
- JSON responses: `{"ok":true,"data":{...}}` / `{"ok":false,"error":"..."}`
- Never edit `src/index_html.h` by hand — edit `web/index.html` and rebuild
- Cross-compile with `arm-linux-gnueabihf-gcc` (Pi 4 = ARMv7)
- SQLite is the only external dependency at runtime

---

## Skill system

This project uses a **progressive disclosure skill system** to give Claude
targeted knowledge about specific areas of the codebase without loading
everything at once.

```
skills/
  manifest.json          ← index of all skills (name, description, path)
  <skill-name>/
    SKILL.md             ← purpose, files, patterns, step-by-step, tests
```

**For Claude (Planner):** Read `skills/manifest.json` before writing any plan.
If the user's request matches a skill, load that skill's `SKILL.md` to inform
the spec and tasks. Never load all skills — only the relevant one(s).

**For the user:** To see available skills:
```bash
./scripts/load_skill.sh list
```

To print a skill's content:
```bash
./scripts/load_skill.sh <skill-name>
```

To add a new skill and register it:
```bash
cp -r skills/example/ skills/my-skill/
# edit skills/my-skill/SKILL.md
./scripts/update-manifest.sh
```

---

## Planner role (Claude)

Claude acts exclusively as **Planner** in this project. See full instructions in
`.claude/planner-instructions.md`.

**Never write implementation code directly.** Always create a plan first in
`.plans/YYYY-MM-DD-feature-name/` with three files:
- `spec.md` — goals, constraints, design decisions, out-of-scope
- `tasks.md` — ordered `[ ]` checklist with exact file paths and line numbers
- `tests.md` — acceptance criteria with exact commands to verify each task

### Karpathy principles

Every plan must satisfy all four principles before being handed to the Executor:

| Principle | Enforced by |
|---|---|
| **Think Before Planning** | Write `spec.md` before `tasks.md`. No exceptions. |
| **Simplicity First** | `spec.md` must have an "Out of scope" section justifying what was excluded. |
| **Surgical Changes** | Every task names exact file + symbol + line number. |
| **Goal-Driven Execution** | Every task group has a test that verifies user-visible behavior. |

---

## Workflow

This project uses the **Planner-Executor** workflow:

1. Ask Claude to create a plan → `.plans/YYYY-MM-DD-feature/`
2. Ask Copilot to implement the plan in VS Code
3. Relay failures from Copilot back to Claude for plan revision

See `README.md` for the full workflow guide.

---

## Out-of-scope for Claude to implement directly

- Production deployments (`make deploy` on a live Pi)
- Database migrations on live data
- Secrets / credentials management

---

## Notes

- Cross-compiler must be installed: `sudo apt install gcc-arm-linux-gnueabihf`
- SQLite dev headers must be installed: `sudo apt install libsqlite3-dev`
- `xxd` is required to regenerate `src/index_html.h`: `sudo apt install xxd`
- The ARM binary is named `appbooking-pi`; the native binary is `appbooking`
- Pi deploy targets assume SSH key auth to the hosts defined in `Makefile`
