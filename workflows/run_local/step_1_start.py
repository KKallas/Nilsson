"""Launch the project's separate server locally; pause with Stop in the queue."""

from __future__ import annotations

import json
import os
import socket
import subprocess
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


def _pid_alive(pid: int) -> bool:
    """True if the process exists (signal 0 = liveness probe, no signal sent)."""
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False
    except OSError:
        return False


def _reuse_existing(spec) -> dict | None:
    """Issue #9 Fix B: if a previous Nilsson run left a project server
    alive (orphaned child — children survive parent exit by default on
    POSIX), reconnect to it instead of spawning a duplicate.

    Returns a ready-to-return pause dict on reuse, or None to fall through
    to a fresh ``Popen``. Stale markers (pid is dead) are cleaned here so
    the next step starts from a clean slate."""
    if not SESSION_FILE.exists():
        return None
    try:
        sess = json.loads(SESSION_FILE.read_text())
    except (OSError, json.JSONDecodeError):
        SESSION_FILE.unlink(missing_ok=True)
        return None
    pid = sess.get("pid")
    if not isinstance(pid, int) or not _pid_alive(pid):
        SESSION_FILE.unlink(missing_ok=True)
        return None
    # Sanity-check: the running pid's recorded `start` should match the
    # current descriptor's `start`. If a different project has been
    # configured in the meantime, the stale subprocess isn't ours to reuse.
    if sess.get("start") != list(spec.start):
        return None
    url = sess.get("url") or ""
    return _pause_result(spec, pid, url, reused=True)


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

    # Issue #9 Fix B: reconnect to an orphaned previous run rather than
    # double-spawning. If the marker points at a dead pid it gets cleaned
    # here and we fall through to a fresh Popen.
    reused = _reuse_existing(spec)
    if reused is not None:
        return reused

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

    # Embedding the served project in the dashboard is the `show_dashboard`
    # workflow's job now (autostart it alongside this one). Keeps each
    # workflow doing one thing.
    return _pause_result(spec, proc.pid, url, reused=False)


def _pause_result(spec, pid: int, url: str, *, reused: bool) -> dict:
    """The pause-with-Stop dict — shared by fresh-launch and Fix-B reuse."""
    reused_note = ""
    if reused:
        reused_note = (
            "<p style=\"font-size:13px;color:#3fb950;\">"
            "Reconnected to an existing process from a previous Nilsson "
            "session (pid alive)."
            "</p>"
        )
    return {
        "ok": True,
        "pause": True,
        "title": "Project server running",
        "detail_html": (
            "<h3>Project server running</h3>"
            f"<p>Launched with: <code>{' '.join(spec.start)}</code> "
            f"(pid {pid}).</p>"
            f"<p style=\"margin:12px 0;\"><a href=\"{url}\" target=\"_blank\" "
            "style=\"display:inline-block;padding:8px 20px;background:#58a6ff;"
            "color:#fff;border-radius:6px;text-decoration:none;"
            f"font-weight:600;font-size:14px;\">Open {url}</a></p>"
            f"{reused_note}"
            "<p style=\"font-size:13px;color:#8b949e;\">Nilsson stays on its "
            "own port (loopback). Click <b>Stop</b> to terminate. "
            "Run <code>show_dashboard</code> to embed this page in the "
            "dashboard alongside the chat.</p>"
        ),
        "actions": [{"label": "Stop", "action": "continue"}],
        "output": f"Project server pid={pid} at {url}"
                  + (" (reused)" if reused else ""),
    }
