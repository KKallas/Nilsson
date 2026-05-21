"""Stop the dashboard view — bookkeeping only; the project keeps running.

We deliberately don't delete the widget HTML in public/charts/: that
artifact is small, harmless, and lets the user reopen the view from the
chat history without re-running the workflow. Older artifacts can be
cleaned by the standard chat-cleanup tools. We DO clear the
``.nilsson/dashboard_active.json`` marker so the chat UI stops
auto-loading the widget on page reload."""

from __future__ import annotations

from pathlib import Path

ACTIVE_FILE = Path(".nilsson/dashboard_active.json")


def run(context):
    if ACTIVE_FILE.exists():
        try:
            ACTIVE_FILE.unlink()
        except OSError:
            pass
    return {
        "ok": True,
        "output": "Dashboard view ended. The project server keeps running; "
                  "stop it via the run_local queue item.",
    }
