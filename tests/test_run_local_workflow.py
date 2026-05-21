"""Tests for the run_local workflow's safety guards (no subprocess launched).

Run: `python tests/test_run_local_workflow.py`  (no pytest; exit 0/1)

Covers the refusal paths in step_1 (no descriptor, target=remote, port
collision) and the cleanup paths in step_2 (no session, dead pid). The
happy-path Popen is exercised manually end-to-end via `run_workflow`.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

fails: list[str] = []
tmps: list[Path] = []


def ok(name: str, cond: bool) -> None:
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name)


def load_step(name: str):
    """Load a step file as a fresh module so we can call its run()."""
    path = ROOT / "workflows" / "run_local" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"_step_{name}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def with_dir(cfg: dict | None = None) -> Path:
    d = Path(tempfile.mkdtemp(prefix="runlocal-"))
    tmps.append(d)
    if cfg is not None:
        (d / ".nilsson").mkdir(parents=True)
        (d / ".nilsson" / "config.json").write_text(json.dumps(cfg))
    return d


orig_cwd = Path.cwd()
# server.paths.PROJECT_DIR + NILSSON_DIR are module attributes; reset per test.
import server.paths as _paths                                  # noqa: E402
_orig_project_dir = _paths.PROJECT_DIR
_orig_nilsson_dir = _paths.NILSSON_DIR


def point_project_at(d: Path) -> None:
    _paths.PROJECT_DIR = d


def hide_bundled_default(d: Path) -> None:
    """Point NILSSON_DIR at an empty dir so the bundled minesweeper
    auto-default does NOT fire — for tests that need the raw 'no
    descriptor + no bundle' path."""
    _paths.NILSSON_DIR = d


try:
    step1 = load_step("step_1_start")
    step2 = load_step("step_2_stop")

    # --- step_1 refusals (none of these should launch a subprocess) ----

    # absent descriptor AND no bundled default → fail cleanly. (When the
    # bundled minesweeper is present the auto-default would step in and
    # launch it instead; that path is verified by test_default_project.)
    d = with_dir(None)
    nd = with_dir(None)                                 # empty NILSSON_DIR
    point_project_at(d)
    hide_bundled_default(nd)
    os.chdir(d)
    r = step1.run({})
    ok("no descriptor + no bundle -> fail", r["ok"] is False
       and "no `project` block" in r["error"])
    ok("no descriptor + no bundle -> no pause", not r.get("pause"))
    _paths.NILSSON_DIR = _orig_nilsson_dir              # restore for next tests

    # target=remote → refuse (this workflow is run_local)
    d = with_dir({"project": {"start": ["python", "-V"], "target": "remote",
                              "remote": {"url": "https://x"}}})
    point_project_at(d)
    os.chdir(d)
    r = step1.run({})
    ok("target=remote -> fail", r["ok"] is False
       and "use the run_remote" in r["error"])

    # port collision with Nilsson's port
    os.environ["RENDER_PORT"] = "8421"
    d = with_dir({"project": {"start": ["python", "-V"], "port": 8421}})
    point_project_at(d)
    os.chdir(d)
    r = step1.run({})
    ok("port collision -> fail", r["ok"] is False
       and "port collision" in r["error"])
    del os.environ["RENDER_PORT"]

    # --- step_2 cleanup paths -------------------------------------------

    # no session file → returns ok with a clean message
    d = with_dir(None)
    os.chdir(d)
    r = step2.run({})
    ok("step_2 no session -> ok", r["ok"] and "No run_local session" in r["output"])

    # session pointing to a long-dead pid (1 = init, but treat as 'alive';
    # use a pid that almost certainly isn't ours — 0 is invalid)
    d = with_dir(None)
    os.chdir(d)
    (d / ".nilsson").mkdir(parents=True)
    # 2**30 PID will not exist on any sane system
    (d / ".nilsson" / "run_local.json").write_text(
        json.dumps({"pid": 2**30, "url": "http://x"}))
    r = step2.run({})
    ok("step_2 dead pid -> cleaned",
       r["ok"] and "not running" in r["output"]
       and not (d / ".nilsson" / "run_local.json").exists())

    # --- Fix B: reconnect to a live previous run instead of Popening again
    # Use sys.executable for the actual command (`python` isn't always on
    # PATH on macOS) — `<py> -V` exits immediately, safe to invoke.

    # Live pid + matching start → reuse path (no new subprocess; pause
    # marked "reused"). We point at our own pid (definitely alive) and
    # match `start` exactly so the spec-check passes.
    spec_start = [sys.executable, "-V"]
    d = with_dir({"project": {"start": spec_start, "port": 12321}})
    point_project_at(d)
    os.chdir(d)
    (d / ".nilsson").mkdir(parents=True, exist_ok=True)
    (d / ".nilsson" / "run_local.json").write_text(json.dumps({
        "pid": os.getpid(), "url": "http://1.2.3.4:12321",
        "port": 12321, "start": spec_start,
    }))
    r = step1.run({})
    ok("Fix B: live pid + matching start -> reuse",
       r.get("pause") and "reused" in r.get("output", ""))

    # Live pid but mismatching `start` (different project configured since)
    # → don't reuse; fall through to Popen with the current spec.start.
    d = with_dir({"project": {"start": spec_start, "port": 12322}})
    point_project_at(d)
    os.chdir(d)
    (d / ".nilsson").mkdir(parents=True, exist_ok=True)
    (d / ".nilsson" / "run_local.json").write_text(json.dumps({
        "pid": os.getpid(), "url": "http://x",
        "port": 12322, "start": ["different", "command"],
    }))
    r = step1.run({})
    ok("Fix B: live pid + different start -> don't reuse",
       r.get("pause") and "reused" not in r.get("output", ""))
finally:
    os.chdir(orig_cwd)
    _paths.PROJECT_DIR = _orig_project_dir
    _paths.NILSSON_DIR = _orig_nilsson_dir
    os.environ.pop("NILSSON_PROJECT_DIR", None)
    os.environ.pop("RENDER_PORT", None)
    for d in tmps:
        shutil.rmtree(d, ignore_errors=True)

if fails:
    print(f"\n{len(fails)} failed: {fails}")
    sys.exit(1)
print("\nAll run_local workflow guard tests passed.")
