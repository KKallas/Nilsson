"""Stop the dashboard view — bookkeeping only; the project keeps running.

We deliberately don't delete the widget HTML in public/charts/: that
artifact is small, harmless, and lets the user reopen the view from the
chat history without re-running the workflow. Older artifacts can be
cleaned by the standard chat-cleanup tools."""

from __future__ import annotations


def run(context):
    return {
        "ok": True,
        "output": "Dashboard view ended. The project server keeps running; "
                  "stop it via the run_local queue item.",
    }
