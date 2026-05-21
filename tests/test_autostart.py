"""Tests for tools/nilsson/_autostart.py (generic startup.autostart)."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.nilsson._autostart import (                          # noqa: E402
    compute_autostart, DEFAULT_WHEN_PROJECT_PRESENT,
)
import server.paths as _paths                                   # noqa: E402

fails: list[str] = []
tmps: list[Path] = []
_orig_nilsson_dir = _paths.NILSSON_DIR


def ok(name: str, cond: bool) -> None:
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name)


def D(cfg: object | None = None) -> Path:
    d = Path(tempfile.mkdtemp(prefix="autostart-"))
    tmps.append(d)
    if cfg is not None:
        (d / ".nilsson").mkdir(parents=True)
        (d / ".nilsson" / "config.json").write_text(
            cfg if isinstance(cfg, str) else json.dumps(cfg))
    return d


def hide_bundle() -> None:
    """Point NILSSON_DIR at an empty dir so the auto-default project does
    NOT register — lets us test the no-default-fallback paths."""
    nd = Path(tempfile.mkdtemp(prefix="empty-nd-"))
    tmps.append(nd)
    _paths.NILSSON_DIR = nd


try:
    # Explicit list → honored exactly, in order.
    r = compute_autostart(D({"startup": {"autostart": ["a", "b", "c"]}}))
    ok("explicit list honored in order", r == ["a", "b", "c"])

    # Explicit empty [] → opt-out (honored even if a project is loadable).
    r = compute_autostart(D({"startup": {"autostart": []},
                             "project": {"start": ["x"]}}))
    ok("explicit [] opts out", r == [])

    # Whitespace-only / empty strings filtered out.
    r = compute_autostart(D({"startup": {"autostart": ["a", "", "  "]}}))
    ok("blank entries filtered", r == ["a"])

    # Mixed types (numbers) → treat as unset, fall back to default policy.
    hide_bundle()
    r = compute_autostart(D({"startup": {"autostart": [1, 2]}}))
    ok("bad types -> default policy (no project, no bundle => [])", r == [])
    _paths.NILSSON_DIR = _orig_nilsson_dir

    # Absent + project configured → default fallback.
    r = compute_autostart(D({"project": {"start": ["python", "app.py"]}}))
    ok("absent + project -> default fallback",
       r == list(DEFAULT_WHEN_PROJECT_PRESENT))

    # Absent + bundled default present (this repo) → default fallback.
    r = compute_autostart(D(None))
    bundled = ROOT / "examples" / "minesweeper" / "app.py"
    if bundled.exists():
        ok("absent + bundled minesweeper -> default fallback",
           r == list(DEFAULT_WHEN_PROJECT_PRESENT))
    else:
        ok("absent + no bundle -> []", r == [])

    # Absent + no project + bundle hidden → [] (no autostart).
    hide_bundle()
    r = compute_autostart(D(None))
    ok("absent + nothing loadable -> []", r == [])
    _paths.NILSSON_DIR = _orig_nilsson_dir

    # Malformed config (bad JSON) → fall back to default policy (here:
    # bundle present, so default).
    r = compute_autostart(D("{not json"))
    if bundled.exists():
        ok("bad json -> default (bundle present)",
           r == list(DEFAULT_WHEN_PROJECT_PRESENT))
    else:
        ok("bad json + no bundle -> []", r == [])

    # `startup` is not a dict → treat as unset.
    r = compute_autostart(D({"startup": "nope"}))
    if bundled.exists():
        ok("startup not object -> default", r == list(DEFAULT_WHEN_PROJECT_PRESENT))

    # `startup.autostart` not a list → treat as unset.
    r = compute_autostart(D({"startup": {"autostart": "run_local"}}))
    if bundled.exists():
        ok("autostart not list -> default", r == list(DEFAULT_WHEN_PROJECT_PRESENT))

    # Remote target → default policy still uses the same list (caller can
    # decide what to do); compute_autostart's loadable-check only excludes
    # remote, so on remote-only we go to []. Verify:
    hide_bundle()
    r = compute_autostart(D({"project": {"start": ["x"], "target": "remote",
                                          "remote": {"url": "https://x"}}}))
    ok("absent autostart + remote target -> []", r == [])
    _paths.NILSSON_DIR = _orig_nilsson_dir
finally:
    _paths.NILSSON_DIR = _orig_nilsson_dir
    for d in tmps:
        shutil.rmtree(d, ignore_errors=True)

if fails:
    print(f"\n{len(fails)} failed: {fails}")
    sys.exit(1)
print("\nAll autostart tests passed.")
