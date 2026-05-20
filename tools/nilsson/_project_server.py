"""tools/nilsson/_project_server.py — project-server descriptor helper.

Helper module for the ``run_local`` (and future ``run_remote``) workflows.
Leading-underscore filename keeps it invisible to the tool scanner (it is
not a runnable tool, just a shared parser for workflows).

Lives in ``tools/`` rather than ``server/`` deliberately: per the project
principle, Nilsson core gets touched only when it must (e.g. the bind-
time security invariant). Reading a config file does not require core
access, so it lives here.

## The descriptor

A project declares its separate server in ``.nilsson/config.json`` under
the ``project`` key::

    {
      "project": {
        "start":  ["python", "app.py"],        # argv: launch the server
        "init":   ["python", "app.py", "--init"],  # optional one-time init
        "port":   7700,                          # port it listens on
        "target": "local",                       # "local" | "remote"
        "remote": {
          "url":  "https://example.com",         # base url
          "sync": ["ssh", "host", "..."]         # optional preview hook
        }
      }
    }

Absent ``project`` block ⇒ this project simply has no separate server
(pure tool/workflow project) — that is **not** an error.

Parsing never raises: a malformed descriptor degrades to a clear error
string. Same discipline as the P1 tool scanner.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

VALID_TARGETS = ("local", "remote")
# Bundled default starter project, used when no `project` block is configured.
# Lives in Nilsson's own tree so it's always there until the user replaces it.
_BUNDLED_DEFAULT_REL = ("examples", "minesweeper", "app.py")
_BUNDLED_DEFAULT_PORT = 7700


@dataclass(frozen=True)
class ProjectServer:
    """How Nilsson starts / reaches the project's separate server."""

    start: list[str]
    init: Optional[list[str]]
    port: Optional[int]
    target: str
    remote_url: Optional[str]
    remote_sync: Optional[list[str]]
    source: Path

    @property
    def is_remote(self) -> bool:
        return self.target == "remote"


@dataclass(frozen=True)
class Result:
    spec: Optional[ProjectServer]
    error: Optional[str]

    @property
    def ok(self) -> bool:
        return self.spec is not None

    @property
    def absent(self) -> bool:
        return self.spec is None and self.error is None


def _argv(v: Any) -> Optional[list[str]]:
    if isinstance(v, list) and v and all(isinstance(x, str) and x for x in v):
        return list(v)
    return None


def _bundled_default(cfg_source: Path) -> Optional[ProjectServer]:
    """Synthesize the spec for the bundled default project (minesweeper).

    Returns None if the bundle is missing (e.g., a stripped install). The
    bundle lives in Nilsson's own tree, so it's always there until you
    replace it with your own ``project`` block.
    """
    try:
        from server.paths import NILSSON_DIR
    except Exception:
        return None
    app = NILSSON_DIR.joinpath(*_BUNDLED_DEFAULT_REL)
    if not app.exists():
        return None
    return ProjectServer(
        start=[sys.executable, str(app)],
        init=None,
        port=_BUNDLED_DEFAULT_PORT,
        target="local",
        remote_url=None,
        remote_sync=None,
        source=cfg_source,
    )


def load_project_server(
    project_dir: Path | str | None = None,
    *,
    auto_default: bool = True,
) -> Result:
    """Read + validate the ``project`` descriptor. Never raises.

    When ``auto_default`` is True (the default) and no ``project`` block is
    configured, fall back to the bundled minesweeper at
    ``NILSSON_DIR/examples/minesweeper/`` — Nilsson always ships *something*
    you can replace. Pass ``auto_default=False`` to get the raw "absent"
    behavior (tests use this).
    """
    if project_dir is None:
        from server.paths import PROJECT_DIR as project_dir  # lazy
    cfg_path = Path(project_dir) / ".nilsson" / "config.json"

    def _absent() -> Result:
        if not auto_default:
            return Result(None, None)
        spec = _bundled_default(cfg_path)
        return Result(spec, None) if spec else Result(None, None)

    if not cfg_path.exists():
        return _absent()
    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return Result(None, f"{cfg_path}: {type(exc).__name__}: {exc}")
    if not isinstance(cfg, dict):
        return Result(None, f"{cfg_path}: top level must be an object")

    proj = cfg.get("project")
    if proj is None:
        return _absent()
    if not isinstance(proj, dict):
        return Result(None, "`project` must be an object")

    def bad(msg: str) -> Result:
        return Result(None, f"project descriptor: {msg}")

    start = _argv(proj.get("start"))
    if start is None:
        return bad("`start` must be a non-empty list of strings")

    init = None
    if "init" in proj and proj["init"] is not None:
        init = _argv(proj["init"])
        if init is None:
            return bad("`init` must be a non-empty list of strings")

    port = proj.get("port")
    if port is not None and not (isinstance(port, int) and 1 <= port <= 65535):
        return bad(f"`port` must be 1..65535, got {port!r}")

    target = proj.get("target", "local")
    if target not in VALID_TARGETS:
        return bad(f"`target` must be one of {VALID_TARGETS}, got {target!r}")

    remote_url: Optional[str] = None
    remote_sync: Optional[list[str]] = None
    remote = proj.get("remote")
    if remote is not None:
        if not isinstance(remote, dict):
            return bad("`remote` must be an object")
        url = remote.get("url")
        if url is not None:
            if not (isinstance(url, str)
                    and url.startswith(("http://", "https://"))):
                return bad("`remote.url` must be an http(s) URL")
            remote_url = url
        if "sync" in remote and remote["sync"] is not None:
            remote_sync = _argv(remote["sync"])
            if remote_sync is None:
                return bad("`remote.sync` must be a non-empty list of strings")

    if target == "remote" and not remote_url:
        return bad("`target` is 'remote' but `remote.url` is missing")

    return Result(
        ProjectServer(
            start=start, init=init, port=port, target=target,
            remote_url=remote_url, remote_sync=remote_sync, source=cfg_path,
        ),
        None,
    )
