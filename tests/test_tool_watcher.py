"""Tests for server/tool_watcher.py.

Run directly: `python tests/test_tool_watcher.py`
No pytest. Asserts → exit 0 on success, exit 1 on failure.

Verifies the two safety properties that make "just drop a file" safe:
  - stat-twice debounce: a change is applied only when (size, mtime) is
    stable across two consecutive polls (no mid-write loads)
  - ast.parse gate: a broken file is skipped, never applied, no crash
plus add / delete detection and the prime() no-spurious-reload baseline.
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from server.tool_watcher import ToolWatcher  # noqa: E402

failures: list[str] = []


def check(name: str, cond: bool) -> None:
    print(f"{'PASS' if cond else 'FAIL'}  {name}")
    if not cond:
        failures.append(name)


def write(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    # Distinct mtime so successive writes are detectable on coarse clocks.
    t = time.time()
    os.utime(p, (t, t))


tmp = Path(tempfile.mkdtemp(prefix="watcher-test-"))
try:
    grp = tmp / "grp"
    grp.mkdir()

    reloads = {"n": 0}

    def fake_reload() -> None:
        reloads["n"] += 1

    w = ToolWatcher(roots=(tmp,), reload_fn=fake_reload)

    # prime() on an empty tree: nothing baselined, no reload.
    w.prime()
    w.poll_once()
    check("empty tree -> no reload", reloads["n"] == 0)

    # 1. New valid file: not applied on first sighting (unstable),
    #    applied on the second poll (stable across two polls).
    f = grp / "alpha.py"
    write(f, '"""alpha."""\nprint("hi")\n')
    changed_first = w.poll_once()
    check("new file not applied on first poll", changed_first is False)
    check("no reload yet (debounce)", reloads["n"] == 0)
    changed_second = w.poll_once()
    check("new file applied once stable", changed_second is True)
    check("reload fired exactly once", reloads["n"] == 1)

    # Steady state -> no further reloads.
    w.poll_once()
    w.poll_once()
    check("steady state -> still 1 reload", reloads["n"] == 1)

    # 2. Mid-write simulation: size keeps changing between polls -> never
    #    applied until it stabilizes.
    g = grp / "beta.py"
    write(g, '"""beta part..."""\n')
    w.poll_once()                       # first sighting
    write(g, '"""beta part... more"""\nx = 1\n')  # changed before 2nd poll
    w.poll_once()                       # unstable -> not applied
    check("mid-write not applied", reloads["n"] == 1)
    # Now leave it alone for two polls -> applied.
    w.poll_once()
    w.poll_once()
    check("stabilized file applied", reloads["n"] == 2)

    # 3. Broken file: skipped, never applied, no crash, no reload.
    b = grp / "broken.py"
    write(b, "def oops(:\n")
    w.poll_once()
    w.poll_once()
    check("broken file does not reload", reloads["n"] == 2)
    w.poll_once()
    check("broken file still skipped", reloads["n"] == 2)

    # 3b. Broken file fixed -> becomes loadable -> applied.
    write(b, '"""now valid."""\n')
    w.poll_once()
    w.poll_once()
    check("fixed file gets applied", reloads["n"] == 3)

    # 4. Deletion: gone for two consecutive polls -> applied (removed).
    f.unlink()
    w.poll_once()
    w.poll_once()
    check("deletion detected", reloads["n"] == 4)

    # 5. .step.py templates and dunder files are ignored.
    write(grp / "thing.step.py", '"""tmpl."""\n')
    write(grp / "_helper.py", '"""priv."""\n')
    w.poll_once()
    w.poll_once()
    check("step/dunder files ignored", reloads["n"] == 4)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

if failures:
    print(f"\n{len(failures)} failure(s): {failures}")
    sys.exit(1)
print("\nAll tool_watcher tests passed.")
