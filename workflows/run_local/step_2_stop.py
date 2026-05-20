"""Stop the project server started by step_1; clean up the session marker."""

from __future__ import annotations

import json
import os
import signal
import time
from pathlib import Path

SESSION_FILE = Path(".nilsson/run_local.json")
_TERM_GRACE_S = 5.0


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False
    except OSError:
        return False


def run(context):
    if not SESSION_FILE.exists():
        return {"ok": True, "output": "No run_local session to stop."}

    try:
        session = json.loads(SESSION_FILE.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        SESSION_FILE.unlink(missing_ok=True)
        return {"ok": True,
                "output": f"Session marker unreadable ({exc}); removed."}

    pid = session.get("pid")
    url = session.get("url", "")

    if not isinstance(pid, int) or not _alive(pid):
        SESSION_FILE.unlink(missing_ok=True)
        return {"ok": True,
                "output": f"Process not running (cleaned marker for {url})."}

    # SIGTERM, then SIGKILL after a short grace period.
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError as exc:
        return {"ok": False, "error": f"SIGTERM failed: {exc}",
                "output": f"could not signal pid {pid}: {exc}"}

    deadline = time.monotonic() + _TERM_GRACE_S
    while time.monotonic() < deadline and _alive(pid):
        time.sleep(0.1)

    method = "SIGTERM"
    if _alive(pid):
        try:
            os.kill(pid, signal.SIGKILL)
            method = "SIGKILL"
        except OSError:
            pass

    SESSION_FILE.unlink(missing_ok=True)
    return {"ok": True,
            "output": f"Stopped project server pid={pid} via {method} "
                      f"({url})."}
