"""server/project_server.py — the project-server descriptor (issue #9).

Security model (decided): Nilsson is the **local control/authoring plane**
(agent, tools, admin, git) and binds loopback only. The *project* runs as
a **separate server** — the execution plane — which may bind LAN/public and
also runs scheduled workflows, but carries no agent/authoring surface.

This module does NOT mount anything in-process (that earlier approach was
abandoned: same process = same privilege = the public surface sharing the
agent's address space). It only *describes* how Nilsson should start /
initialize / reach the project's own separate server.

## The descriptor

A project declares, in ``.nilsson/config.json`` under a ``project`` key::

    {
      "project": {
        "start":  ["python", "app.py"],        # argv: launch the server
        "init":   ["python", "app.py", "--init"],  # optional one-time init
        "port":   7700,                          # port it listens on
        "target": "local",                       # "local" | "remote"
        "remote": {
          "url":  "https://game.example.com",    # base url (freshness check)
          "sync": ["ssh", "host", "..."]         # pluggable preview/deploy hook
        }
      }
    }

Absent ``project`` block ⇒ this project simply has no separate server
(pure tool/workflow project) — that is **not** an error.

Parsing never raises: a malformed descriptor degrades to a clear error
string, exactly like the tool scanner skips a broken tool.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

VALID_TARGETS = ("local", "remote")


@dataclass(frozen=True)
class ProjectServer:
    """How Nilsson starts / reaches the project's separate server."""

    start: list[str]                 # argv to launch the server
    init: Optional[list[str]]        # optional one-time init argv
    port: Optional[int]              # port it listens on (health/preview)
    target: str                      # "local" | "remote"
    remote_url: Optional[str]        # base url when target/preview is remote
    remote_sync: Optional[list[str]] # pluggable preview/deploy hook (argv)
    source: Path                     # the config.json it came from

    @property
    def is_remote(self) -> bool:
        return self.target == "remote"


@dataclass(frozen=True)
class Result:
    """Outcome. ``spec`` set ⇒ ok. ``error`` set ⇒ present but invalid.
    Both ``None`` ⇒ absent (a project need not have a server)."""

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


def load_project_server(project_dir: Path | str | None = None) -> Result:
    """Read + validate the ``project`` descriptor. Never raises."""
    if project_dir is None:
        from server.paths import PROJECT_DIR as project_dir  # lazy
    cfg_path = Path(project_dir) / ".nilsson" / "config.json"

    if not cfg_path.exists():
        return Result(None, None)  # absent — fine
    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return Result(None, f"{cfg_path}: {type(exc).__name__}: {exc}")
    if not isinstance(cfg, dict):
        return Result(None, f"{cfg_path}: top level must be an object")

    proj = cfg.get("project")
    if proj is None:
        return Result(None, None)  # no server in this project — fine
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
