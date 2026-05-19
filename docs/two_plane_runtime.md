# Two-plane runtime (issue #9)

Nilsson runs as **two separate processes** with different privilege, for
security:

```
 CONTROL / AUTHORING plane            EXECUTION plane
 ─────────────────────────           ──────────────────────────
 local Nilsson                        the project's own server
  • agent, tools, admin, git   ──┐     • the app (may bind LAN/public)
  • binds 127.0.0.1 ONLY         │     • + Nilsson workflow/cron scheduler
  • killable; never exposed      │     • NO agent / admin / authoring
                                 │
        local edit → preview ────┘────► (target=remote) → maybe PR
```

## Security invariant

The agent runs code, edits files, drives git — so it must answer
**loopback only** and be killable. `server/netguard.py` enforces this:
the control server refuses to start on anything non-loopback (especially
`0.0.0.0`). The execution plane runs **version-controlled** workflows but
exposes **no interactive agent and no authoring surface** — reaching it
yields a fixed runner, not a console to mint tools or rewrite config.
Changing what it does always routes back through the control plane → PR.

`server/runtime.py` asserts `server.render_route` is never imported into
it — that assertion *is* the boundary.

## The project descriptor

A project declares its separate server in `.nilsson/config.json`:

```json
{
  "project": {
    "start":  ["python", "app.py"],
    "init":   ["python", "app.py", "--init"],
    "port":   7700,
    "target": "local",
    "remote": {
      "url":  "https://game.example.com",
      "sync": ["ssh", "host", "cd app && git fetch && git checkout -B preview origin/preview && systemctl restart app"]
    }
  }
}
```

- No `project` block ⇒ the project has no separate server (pure
  tool/workflow project) — not an error.
- `target: local` (default) → the project server runs on your machine.
- `target: remote` → it is **not** run locally; `start` is freshness-checked
  at `remote.url` and you use `preview` to push changes.
- `remote.sync` is a **pluggable hook** (any argv) — no deploy infra is
  baked in. Absent ⇒ `preview` prints the manual command instead.

Loaded by `server/project_server.py` (never raises; a malformed
descriptor degrades to a clear error, Nilsson still starts).

## Commands

- **`python start.py`** — the one command. Always starts the control
  plane (loopback); also starts the project server locally when
  `target=local`. `--plan` prints the decision without launching;
  `--init` runs the project's one-time init first.
- **`python -m server.runtime`** — the headless execution runtime
  (project server + workflow scheduler, no agent). What runs remotely, or
  as the local project process under `start.py`.
- **`python tools/nilsson/preview.py`** — capture working changes to the
  `preview` branch (without touching your branch/working tree) and trigger
  the remote `sync` hook so you can *see* them live before opening a PR.
  Preview ≠ deploy; production is still the PR/merge path.

## What this is not

No deploy daemon, no production push from Nilsson, no in-process mount of
the project app into the agent's address space (that earlier approach was
abandoned as a privilege-separation violation).
