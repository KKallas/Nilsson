"""Tests for server/project_server.py (issue #9).

Run: `python tests/test_project_server.py`
No pytest. Exit 0 = pass, 1 = fail.

Covers the project-server descriptor: absence is not an error, JSON/shape
guards, the start/init/port/target/remote validation, and a valid full
descriptor. Never raises. No fastapi needed (pure JSON + dataclass).
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from server.project_server import load_project_server  # noqa: E402

fails: list[str] = []
tmps: list[Path] = []


def ok(name: str, cond: bool) -> None:
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name)


def D(cfg: object | None) -> Path:
    """Make a temp PROJECT_DIR; write .nilsson/config.json if cfg given."""
    d = Path(tempfile.mkdtemp(prefix="psrv-"))
    tmps.append(d)
    if cfg is not None:
        (d / ".nilsson").mkdir(parents=True)
        (d / ".nilsson" / "config.json").write_text(
            cfg if isinstance(cfg, str) else json.dumps(cfg))
    return d


try:
    # absent: no config.json at all
    r = load_project_server(D(None))
    ok("no config -> absent", r.absent and not r.ok and r.error is None)

    # absent: config without a `project` block
    r = load_project_server(D({"llm": {"model": "x"}}))
    ok("no project block -> absent", r.absent)

    # invalid JSON
    r = load_project_server(D("{not json"))
    ok("bad json -> error", not r.ok and "JSONDecodeError" in (r.error or ""))

    # top-level not an object
    r = load_project_server(D("[1,2,3]"))
    ok("non-object top -> error", not r.ok and "object" in (r.error or ""))

    # project not an object
    r = load_project_server(D({"project": "nope"}))
    ok("project not object -> error",
       not r.ok and "must be an object" in (r.error or ""))

    # missing start
    r = load_project_server(D({"project": {"port": 80}}))
    ok("missing start -> error", not r.ok and "`start`" in (r.error or ""))

    # start not list-of-nonempty-str
    r = load_project_server(D({"project": {"start": ["", "x"]}}))
    ok("bad start -> error", not r.ok and "`start`" in (r.error or ""))

    # bad init
    r = load_project_server(
        D({"project": {"start": ["a"], "init": "x"}}))
    ok("bad init -> error", not r.ok and "`init`" in (r.error or ""))

    # bad port
    r = load_project_server(
        D({"project": {"start": ["a"], "port": 99999}}))
    ok("bad port -> error", not r.ok and "`port`" in (r.error or ""))

    # bad target
    r = load_project_server(
        D({"project": {"start": ["a"], "target": "cloud"}}))
    ok("bad target -> error", not r.ok and "`target`" in (r.error or ""))

    # remote target without remote.url
    r = load_project_server(
        D({"project": {"start": ["a"], "target": "remote"}}))
    ok("remote w/o url -> error",
       not r.ok and "remote.url` is missing" in (r.error or ""))

    # remote not object
    r = load_project_server(
        D({"project": {"start": ["a"], "remote": 5}}))
    ok("remote not object -> error",
       not r.ok and "`remote` must be an object" in (r.error or ""))

    # remote.url not http(s)
    r = load_project_server(
        D({"project": {"start": ["a"], "remote": {"url": "ftp://x"}}}))
    ok("bad remote.url -> error",
       not r.ok and "remote.url" in (r.error or ""))

    # remote.sync bad
    r = load_project_server(D({"project": {
        "start": ["a"], "remote": {"url": "https://x", "sync": "nope"}}}))
    ok("bad remote.sync -> error",
       not r.ok and "remote.sync" in (r.error or ""))

    # valid minimal
    r = load_project_server(D({"project": {"start": ["python", "app.py"]}}))
    ok("minimal valid", r.ok and r.spec.start == ["python", "app.py"])
    ok("defaults: target local", r.ok and r.spec.target == "local"
       and not r.spec.is_remote)
    ok("defaults: port None / init None",
       r.ok and r.spec.port is None and r.spec.init is None)

    # valid full remote
    r = load_project_server(D({"project": {
        "start": ["python", "app.py"],
        "init": ["python", "app.py", "--init"],
        "port": 7700,
        "target": "remote",
        "remote": {"url": "https://game.example.com",
                   "sync": ["ssh", "host", "deploy"]},
    }}))
    ok("full valid loads", r.ok)
    ok("full: fields", r.ok and r.spec.port == 7700
       and r.spec.init == ["python", "app.py", "--init"]
       and r.spec.is_remote
       and r.spec.remote_url == "https://game.example.com"
       and r.spec.remote_sync == ["ssh", "host", "deploy"])
finally:
    for d in tmps:
        shutil.rmtree(d, ignore_errors=True)

if fails:
    print(f"\n{len(fails)} failed: {fails}")
    sys.exit(1)
print("\nAll project_server tests passed.")
