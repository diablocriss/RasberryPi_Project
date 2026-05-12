# Skill: planner-executor-setup

---

## Purpose

Bootstrap the Planner-Executor workflow into any new project so that Claude acts as Planner and GitHub Copilot acts as Executor, with Karpathy principles enforced throughout.

---

## When to use

- Starting a new project and wanting to install the workflow
- Onboarding a project without `.claude/`, `.github/copilot-instructions.md`, or `skills/`
- Recreating or repairing workflow after config files were deleted

---

## Files involved

| File | Role |
|---|---|
| `CLAUDE.md` | Project context, build commands, Karpathy principles, skill system pointer |
| `.claude/planner-instructions.md` | Claude's full Planner role definition |
| `.github/copilot-instructions.md` | Copilot's full Executor role definition |
| `scripts/init.sh` | One-command setup: detection + config + scaffolding |
| `scripts/detect-project.sh` | Detects project type and outputs build/test commands |
| `scripts/plan-executor.sh` | CLI helper: `new`, `list`, `status`, `open`, `test` |
| `scripts/load_skill.sh` | Lists skills or prints skill content |
| `scripts/update-manifest.sh` | Regenerates `skills/manifest.json` |
| `.planner-executor/config.yaml` | Per-project config: build/test/run/lint commands |
| `skills/manifest.json` | Index of all available skills |
| `.plans/` | All plan folders: `YYYY-MM-DD-feature-name/` |

---

## Constraints and gotchas

- **`CLAUDE.md` is user-owned** — `init.sh --upgrade` never overwrites it.
- **`skills/manifest.json` is auto-generated** — never edit it by hand. Use `update-manifest.sh`.
- **Plans are permanent records** — never delete `.plans/` folders.
- **`init.sh` is idempotent** — safe to run twice.
- **Copilot must run from WSL** on Windows — open VS Code with `code .` from the WSL terminal.

---

## Patterns

### Plan folder structure
```
.plans/
└── YYYY-MM-DD-feature-name/
    ├── spec.md      # Goal, key discoveries, design, files changed, out of scope
    ├── tasks.md     # Ordered [ ] checklist with exact file + line references
    └── tests.md     # Acceptance criteria with exact Pass/Fail conditions
```

### Invoking Claude as Planner
```
Claude, create a plan for <feature>.
Save it to .plans/YYYY-MM-DD-<feature-name>/
Include spec.md, tasks.md, and tests.md.
Follow .claude/planner-instructions.md.
```

### Invoking Copilot as Executor
```
Read the plan in .plans/YYYY-MM-DD-<feature-name>/
Start with spec.md, then tasks.md, then tests.md.
Implement each task in order. Run the test from tests.md after each task.
Mark [x] when the test passes. Stop and report the exact error if a test fails.
```

---

## Step-by-step

1. Run `./scripts/init.sh` from the project root.
2. Review `.planner-executor/config.yaml` — correct any mis-detected commands.
3. Add `.vscode/settings.json` with `"github.copilot.chat.useInstructionFiles": true`.
4. Verify: `./scripts/load_skill.sh list` shows at least one skill.
5. Verify: `./scripts/plan-executor.sh new smoke-test` creates `.plans/YYYY-MM-DD-smoke-test/`.

---

## Tests and verification

```bash
./scripts/load_skill.sh list
```
**Pass:** At least one skill name printed.
**Fail:** "No manifest found" → run `./scripts/update-manifest.sh`.

```bash
./scripts/plan-executor.sh new smoke-test
ls .plans/
```
**Pass:** New folder with spec.md, tasks.md, tests.md.
**Fail:** Permission error or missing `.plans/` → check working directory.
