# Show Dashboard

Embeds the served project's page (the iframe widget pushed by
`tools/render/embed_project.py`) into Nilsson's dashboard drawer so the
live project shows up next to the chat for LLM-driven iteration.

Orthogonal to `run_local`:

- `run_local` manages the project server *lifecycle* (start/stop).
- `show_dashboard` manages the dashboard *view* (push/refresh).

You can run either independently. Typical usage: both are autostarted
(see `startup.autostart` in `examples/project.config.json`) — Nilsson
boots, `run_local` launches the project server on its own port, and
`show_dashboard` pushes the iframe widget. Click **View in dashboard**
in the queue to open it.

## What it does

1. **`step_1_show`** — waits briefly for `run_local`'s session marker
   (`.nilsson/run_local.json`), then invokes `embed_project.py` to push
   the widget. Pauses to the queue with a **View in dashboard** button
   and a **Stop showing** action. If no project server is running after
   the wait, fails cleanly with "start run_local first."
2. **`step_2_clear`** — bookkeeping cleanup on Stop. The widget HTML
   artifact stays in `public/charts/` (harmless; older artifacts pile up
   slowly).

The widget itself has a wait-for-ready overlay (Fix A) — it probes the
project URL before showing the iframe, so a cold-starting subprocess
doesn't paint "site can't be reached" for the first second or two.
