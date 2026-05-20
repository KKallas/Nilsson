# Run Local

Start the project's own server **locally** as a separate process — using
the `project` descriptor in `.nilsson/config.json` (see
`examples/project.config.json`). Pauses to the queue with a Stop button,
exactly like `dev_sync`.

This is the first concrete deliverable of #9: orchestration lives as a
**workflow**, not as bespoke Nilsson code. The only #9-related change in
core is `server/netguard.py` (the pre-bind loopback invariant); everything
else — descriptor parsing, starting/stopping the project server, the
preview/remote flow — lives in `tools/` and `workflows/`.

## What it does

1. **`step_1_start`** — load the descriptor, refuse if `port == Nilsson's
   port` (collision guard), refuse if `target == "remote"` (use a future
   `run_remote` workflow for that), `Popen(spec.start)` in the project
   dir, write a small `.nilsson/run_local.json` session marker (pid + url),
   then pause with the LAN URL and a **Stop** button in the queue.
2. **`step_2_stop`** — on Stop, terminate the pid (`SIGTERM`, then `SIGKILL`
   after a short grace period) and remove the marker.

## Try it

In a project whose `.nilsson/config.json` has a `project` block:

```bash
python tools/nilsson/run_workflow.py run_local --wait
```

The project server runs on its own port; Nilsson keeps its own port. See
the queue popup for the **Stop** button.

## Dashboard embed (issue #14)

When step_1 starts the project server it also invokes
`tools/render/embed_project.py`, which wraps the project URL in an iframe
widget and publishes it via the existing render-tool/artifact pattern
(`public/charts/<id>.html`). The queue popup gets a **View in dashboard**
button alongside the **Open** + **Stop** buttons, so the served project
shows up right next to the chat while you iterate with the agent. The
widget has a Refresh button. Best-effort: if the embed step fails for any
reason the project still runs; the dashboard link just won't appear.

## Not in scope here

`run_remote` workflow, preview push, DigitalOcean image, external
date-string watchdog, and a control-plane metadata marker the future
headless execution runtime will refuse — all follow-ups, deliberately
small steps.
