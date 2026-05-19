"""Tests for start.decide() (issue #9 — startup target selection).

Run: `python tests/test_start_decide.py`  (no pytest; exit 0/1)

decide() is the pure brain of the one startup command: control plane is
always on; absent/broken descriptor never blocks Nilsson; local target
runs the project server here; remote target does not (only a freshness
check + the preview path).
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import start  # noqa: E402
from server.project_server import Result, ProjectServer  # noqa: E402

fails: list[str] = []


def ok(name: str, cond: bool) -> None:
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name)


def spec(target: str, url: str | None = None) -> ProjectServer:
    return ProjectServer(start=["python", "app.py"], init=None, port=7700,
                         target=target, remote_url=url, remote_sync=None,
                         source=Path("/x/.nilsson/config.json"))


# broken descriptor → control only, never blocks Nilsson
p = start.decide(Result(None, "bad `start`"))
ok("broken: control on", p.start_control)
ok("broken: no local project", not p.start_project_local)
ok("broken: no remote check", p.remote_check_url is None)
ok("broken: note explains", "invalid" in p.note)

# absent descriptor → control only
p = start.decide(Result(None, None))
ok("absent: control on", p.start_control and not p.start_project_local)
ok("absent: note explains", "no project server" in p.note)

# local target → control + project server here
p = start.decide(Result(spec("local"), None))
ok("local: control on", p.start_control)
ok("local: project local on", p.start_project_local)
ok("local: no remote check", p.remote_check_url is None)

# remote target → control here, project NOT local, freshness-check the url
p = start.decide(Result(spec("remote", "https://game.example.com"), None))
ok("remote: control on", p.start_control)
ok("remote: project NOT local", not p.start_project_local)
ok("remote: checks the url",
   p.remote_check_url == "https://game.example.com")
ok("remote: note mentions preview", "preview" in p.note)

if fails:
    print(f"\n{len(fails)} failed: {fails}")
    sys.exit(1)
print("\nAll start.decide tests passed.")
