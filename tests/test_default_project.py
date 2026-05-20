"""Tests for the bundled-default-project fallback (issue #9).

When no `project` block is configured, ``load_project_server`` defaults
to the bundled ``examples/minesweeper/app.py`` so Nilsson always ships
*something* you can replace. This is the behavior the user instructed:
"minesweeper is always there as the first thing you can replace."
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import server.paths as _paths                                  # noqa: E402
from tools.nilsson._project_server import (                    # noqa: E402
    load_project_server,
    _bundled_default,
    _BUNDLED_DEFAULT_PORT,
)

fails: list[str] = []
tmps: list[Path] = []


def ok(name: str, cond: bool) -> None:
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name)


def D() -> Path:
    d = Path(tempfile.mkdtemp(prefix="defp-"))
    tmps.append(d)
    return d


bundled = ROOT / "examples" / "minesweeper" / "app.py"
ok("bundled default ships in repo", bundled.exists())

# In this repo, auto_default=True + no config -> returns the bundled spec.
r = load_project_server(D(), auto_default=True)
ok("auto-default kicks in with no config",
   r.ok and r.spec is not None)
ok("auto-default points at bundled minesweeper",
   r.ok and r.spec.start[-1].endswith("examples/minesweeper/app.py"))
ok("auto-default uses bundled port",
   r.ok and r.spec.port == _BUNDLED_DEFAULT_PORT)
ok("auto-default is local",
   r.ok and r.spec.target == "local" and not r.spec.is_remote)
ok("auto-default uses sys.executable (current Python)",
   r.ok and r.spec.start[0] == sys.executable)

# auto_default=False short-circuits — gives the raw "absent" answer.
r = load_project_server(D(), auto_default=False)
ok("auto_default=False -> absent (no auto-default)", r.absent)

# When the bundle is missing, auto-default degrades cleanly to absent.
orig_nilsson_dir = _paths.NILSSON_DIR
try:
    _paths.NILSSON_DIR = Path(tempfile.mkdtemp(prefix="empty-nd-"))
    tmps.append(_paths.NILSSON_DIR)
    spec = _bundled_default(Path("/x/cfg"))
    ok("bundle missing -> no spec", spec is None)
    r = load_project_server(D(), auto_default=True)
    ok("bundle missing + auto_default -> absent", r.absent)
finally:
    _paths.NILSSON_DIR = orig_nilsson_dir
    for d in tmps:
        shutil.rmtree(d, ignore_errors=True)

if fails:
    print(f"\n{len(fails)} failed: {fails}")
    sys.exit(1)
print("\nAll default_project tests passed.")
