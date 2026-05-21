"""tools/nilsson/_autostart.py — compute workflows to autostart on boot.

Generic replacement for the previously-hard-coded "always start run_local"
in ``server/render_route._lifespan``. The boot lifespan now just iterates
this list — keeps orchestration declarative in config, not in core.

Leading-underscore filename keeps it invisible to the tool scanner (this
is a shared helper for the lifespan, not a runnable tool).

## Configuration

In ``.nilsson/config.json``::

    {
      "startup": {
        "autostart": ["run_local", "show_dashboard"]
      }
    }

- A **list** (any length, including empty) is an **explicit choice** —
  honored exactly, including ``[]`` as opt-out of autostart entirely.
- **Absent** ``startup.autostart`` falls back to a sensible default
  (``run_local`` + ``show_dashboard``) **only when a project is loadable**
  (configured or via the bundled-default fallback). On a pure
  tool/workflow project with no separate server, the default is no
  autostart.

Never raises; malformed config degrades to the default-or-empty path.
"""

from __future__ import annotations

import json
from pathlib import Path

DEFAULT_WHEN_PROJECT_PRESENT = ["run_local", "show_dashboard"]


def _read_user_list(cfg_path: Path) -> list[str] | None:
    """Return the user's explicit autostart list, or None when unset.

    None means "fall back to the default policy"; an empty list means
    "user explicitly opted out — autostart nothing"."""
    if not cfg_path.exists():
        return None
    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(cfg, dict):
        return None
    startup = cfg.get("startup")
    if not isinstance(startup, dict):
        return None
    raw = startup.get("autostart")
    if not isinstance(raw, list):
        return None
    cleaned = [n for n in raw if isinstance(n, str) and n.strip()]
    # Distinguish "user set autostart: []" (opt-out) from "any string lost
    # to bad types" (treat as unset). If the raw list had items but all
    # were bad types, fall back to default; if it was genuinely empty,
    # honor that.
    if not cleaned and any(not isinstance(n, str) for n in raw):
        return None
    return cleaned


def compute_autostart(project_dir: Path | str | None = None) -> list[str]:
    """Workflows to start on boot, in order. Never raises."""
    if project_dir is None:
        from server.paths import PROJECT_DIR as project_dir
    cfg_path = Path(project_dir) / ".nilsson" / "config.json"

    user = _read_user_list(cfg_path)
    if user is not None:
        return user                               # explicit choice (incl. [])

    # No explicit config → default only if a project is actually loadable.
    try:
        from tools.nilsson._project_server import load_project_server
        res = load_project_server()
        if res.ok and not res.spec.is_remote:
            return list(DEFAULT_WHEN_PROJECT_PRESENT)
    except Exception:
        pass
    return []
