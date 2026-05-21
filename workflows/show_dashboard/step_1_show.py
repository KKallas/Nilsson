"""Push the served-project iframe widget; pause with View + Stop in the queue.

Pairs with `run_local`: that workflow writes `.nilsson/run_local.json`
(the session marker with the project URL); this workflow reads it via
the `embed_project.py` render tool and pushes the iframe widget. When
both are autostarted in order, the dashboard view appears right after
the project server is live.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

SESSION_FILE = Path(".nilsson/run_local.json")
ACTIVE_FILE = Path(".nilsson/dashboard_active.json")
_WAIT_FOR_SESSION_S = 3.0          # autostart race window with run_local
_WAIT_TICK_S = 0.1


def _nilsson_port() -> int:
    try:
        return int(os.environ.get("RENDER_PORT", "8421"))
    except ValueError:
        return 8421


def _fail(msg: str) -> dict:
    return {"ok": False, "error": msg, "output": msg}


def _wait_for_session() -> bool:
    """Brief poll for the run_local session marker — handles the autostart
    race where run_local and show_dashboard kick off in parallel."""
    deadline = time.monotonic() + _WAIT_FOR_SESSION_S
    while time.monotonic() < deadline:
        if SESSION_FILE.exists():
            return True
        time.sleep(_WAIT_TICK_S)
    return False


def _invoke_embed(nilsson_port: int, title: str) -> str | None:
    """Call tools/render/embed_project.py; return the dashboard URL."""
    try:
        from server.paths import NILSSON_DIR
    except Exception:
        return None
    embed = NILSSON_DIR / "tools" / "render" / "embed_project.py"
    if not embed.exists():
        return None
    try:
        proc = subprocess.run(
            [sys.executable, str(embed),
             "--port", str(nilsson_port), "--title", title],
            capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    m = re.search(r"\[Open in dashboard\]\(([^)]+)\)", proc.stdout)
    return m.group(1) if m else None


def run(context):
    if not _wait_for_session():
        return _fail("no project server running — start the run_local "
                     "workflow first (or add it to startup.autostart).")
    # Sanity: the marker exists, but is it actually pointing at a usable URL?
    try:
        sess = json.loads(SESSION_FILE.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        return _fail(f"session marker unreadable: {exc}")
    project_url = sess.get("url")
    if not project_url:
        return _fail("session marker is missing `url` — re-run run_local.")

    nilsson_port = _nilsson_port()
    dashboard_url = _invoke_embed(nilsson_port, "Project")
    if dashboard_url is None:
        return _fail("embed_project failed — no dashboard widget pushed.")

    # Mark the active dashboard widget so the chat UI can auto-load it on
    # page reload (no extra click). step_2 clears this marker; reload
    # while inactive ⇒ no auto-load. Best-effort — purely UX.
    try:
        ACTIVE_FILE.parent.mkdir(parents=True, exist_ok=True)
        ACTIVE_FILE.write_text(json.dumps(
            {"url": dashboard_url, "project_url": project_url}, indent=2))
    except OSError:
        pass

    return {
        "ok": True,
        "pause": True,
        "title": "Dashboard view active",
        "detail_html": (
            "<h3>Project view in dashboard</h3>"
            "<p>The served project is embedded as an iframe widget — it "
            "shows up in the dashboard drawer alongside the chat.</p>"
            f"<p style=\"margin:12px 0;\"><a href=\"#\" "
            f"onclick=\"event.preventDefault();loadInDashboard('{dashboard_url}')\" "
            "style=\"display:inline-block;padding:8px 20px;background:#58a6ff;"
            "color:#fff;border-radius:6px;text-decoration:none;"
            f"font-weight:600;font-size:14px;\">View in dashboard</a></p>"
            f"<p style=\"font-size:13px;color:#8b949e;\">Iframe target: "
            f"<code>{project_url}</code>. The widget waits for the server "
            "to be ready before showing (no \"site can't be reached\" "
            "flash on cold start). Click <b>Stop showing</b> to end this "
            "workflow; the project itself keeps running.</p>"
        ),
        "actions": [{"label": "Stop showing", "action": "continue"}],
        "output": f"Dashboard view active at {dashboard_url}",
    }
