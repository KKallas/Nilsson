"""Launch the project's separate server locally; pause with Stop in the queue."""

from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import sys
import time
from pathlib import Path

SESSION_FILE = Path(".nilsson/run_local.json")


def _lan_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
        finally:
            s.close()
    except Exception:
        return "127.0.0.1"


def _nilsson_port() -> int:
    try:
        return int(os.environ.get("RENDER_PORT", "8421"))
    except ValueError:
        return 8421


def _fail(msg: str) -> dict:
    return {"ok": False, "error": msg, "output": msg}


def _embed_in_dashboard(nilsson_port: int, title: str = "Project") -> str | None:
    """Push an iframe widget pointing at the project URL to the dashboard.

    Defensive: failures (missing render tool, subprocess error, no parseable
    output) downgrade silently to None — the project still runs; the queue
    popup just won't have a one-click "Open in dashboard" link. The agent
    can always invoke the render tool manually later (issue #14)."""
    try:
        from server.paths import NILSSON_DIR
        embed = NILSSON_DIR / "tools" / "render" / "embed_project.py"
        if not embed.exists():
            return None
        proc = subprocess.run(
            [sys.executable, str(embed), "--port", str(nilsson_port),
             "--title", title],
            capture_output=True, text=True, timeout=10,
        )
        if proc.returncode != 0:
            return None
        m = re.search(r"\[Open in dashboard\]\(([^)]+)\)", proc.stdout)
        return m.group(1) if m else None
    except Exception:
        return None


def run(context):
    # Defensive descriptor load (never raises, matches tool-scanner discipline).
    try:
        from tools.nilsson._project_server import load_project_server
    except Exception as exc:                                 # pragma: no cover
        return _fail(f"cannot import descriptor helper: {exc}")

    res = load_project_server()
    if res.error:
        return _fail(f"project descriptor invalid: {res.error}")
    if res.absent:
        return _fail("no `project` block in .nilsson/config.json — "
                     "this project has no separate server to run.")
    spec = res.spec
    if spec.is_remote:
        return _fail("descriptor target is 'remote' — use the run_remote "
                     "workflow (or change target to 'local').")

    nilsson_port = _nilsson_port()
    if spec.port == nilsson_port:
        return _fail(f"port collision: project.port {spec.port} equals "
                     f"Nilsson's port {nilsson_port}. Pick a different port "
                     "for the project server in .nilsson/config.json.")

    proj_dir = Path(os.environ.get("NILSSON_PROJECT_DIR", str(Path.cwd())))

    try:
        proc = subprocess.Popen(spec.start, cwd=str(proj_dir))
    except (OSError, ValueError) as exc:
        return _fail(f"could not launch {spec.start!r}: {exc}")

    ip = _lan_ip()
    url = f"http://{ip}:{spec.port}" if spec.port else f"http://{ip}"

    SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    SESSION_FILE.write_text(json.dumps({
        "pid": proc.pid,
        "url": url,
        "port": spec.port,
        "start": spec.start,
        "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }, indent=2))

    # Issue #14: auto-embed the served project in the dashboard so LLM-driven
    # iteration shows up right next to the chat. Best-effort; the workflow
    # itself doesn't fail if the embed step does.
    dashboard_url = _embed_in_dashboard(nilsson_port, "Project")
    dashboard_btn = ""
    if dashboard_url:
        dashboard_btn = (
            f"<p style=\"margin:8px 0 12px;\"><a href=\"#\" "
            f"onclick=\"event.preventDefault();loadInDashboard('{dashboard_url}')\" "
            "style=\"display:inline-block;padding:8px 20px;background:#21262d;"
            "color:#c9d1d9;border:1px solid #30363d;border-radius:6px;"
            "text-decoration:none;font-weight:600;font-size:14px;\">"
            "View in dashboard</a></p>"
        )

    return {
        "ok": True,
        "pause": True,
        "title": "Project server running",
        "detail_html": (
            "<h3>Project server running</h3>"
            f"<p>Launched with: <code>{' '.join(spec.start)}</code> "
            f"(pid {proc.pid}).</p>"
            f"<p style=\"margin:12px 0;\"><a href=\"{url}\" target=\"_blank\" "
            "style=\"display:inline-block;padding:8px 20px;background:#58a6ff;"
            "color:#fff;border-radius:6px;text-decoration:none;"
            f"font-weight:600;font-size:14px;\">Open {url}</a></p>"
            f"{dashboard_btn}"
            "<p style=\"font-size:13px;color:#8b949e;\">Nilsson stays on its "
            "own port (loopback). Click <b>Stop</b> to terminate.</p>"
        ),
        "actions": [{"label": "Stop", "action": "continue"}],
        "output": f"Project server pid={proc.pid} at {url}",
    }
