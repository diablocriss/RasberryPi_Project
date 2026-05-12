# Skill: example

> This is a template skill. Copy this folder, rename it, and fill in the
> sections below. Then run `./scripts/update-manifest.sh` to register it.

---

## Purpose

Describe what this skill covers in one or two sentences. This first sentence is
extracted automatically as the manifest description, so make it self-contained.

---

## When to use

- "I want to add a [feature]…"
- "How do I [task]…"
- Requests touching files in `[path/]`

---

## Files involved

| File | Role |
|---|---|
| `path/to/file.ext` | What it does |

---

## Constraints and gotchas

- [e.g., "Never edit src/index_html.h by hand — edit web/index.html and rebuild"]

---

## Patterns

```c
// Example C pattern
void handler(int fd, const char *body) {
    // parse, call domain logic, respond
}
```

---

## Step-by-step (common task)

1. [Step 1 — what to do and in which file]
2. [Step 2]
3. [Step 3 — including any verification step]

---

## Tests and verification

```bash
make clean && make
./appbooking -p 8080 -d /tmp/test.db &
curl -s http://localhost:8080/api/[endpoint] | jq .
kill %1
```

**Pass:** [what success looks like]
**Fail:** [what to report and to whom]
