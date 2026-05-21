"""Tests for the show_dashboard workflow (safety + happy-path)."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def load_step(path: Path):
    spec = importlib.util.spec_from_file_location(
        "_show_step_" + path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


fails: list[str] = []
tmps: list[Path] = []


def ok(name: str, cond: bool) -> None:
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name)


orig_cwd = Path.cwd()
step1 = load_step(ROOT / "workflows" / "show_dashboard" / "step_1_show.py")
step2 = load_step(ROOT / "workflows" / "show_dashboard" / "step_2_clear.py")

try:
    # Speed up the test: don't actually wait 3s for the session marker.
    step1._WAIT_FOR_SESSION_S = 0.3                              # noqa: SLF001

    # 1. No session marker → fail with clear "start run_local first".
    d = Path(tempfile.mkdtemp(prefix="show-")); tmps.append(d)
    os.chdir(d)
    t0 = time.monotonic()
    r = step1.run({})
    elapsed = time.monotonic() - t0
    ok("no marker -> fail", r["ok"] is False
       and "no project server running" in r["error"])
    ok("no marker -> waited only briefly", elapsed < 2.0)

    # 2. Session marker missing `url` → fail cleanly.
    d = Path(tempfile.mkdtemp(prefix="show-")); tmps.append(d)
    (d / ".nilsson").mkdir(parents=True)
    (d / ".nilsson" / "run_local.json").write_text(json.dumps({"pid": 42}))
    os.chdir(d)
    r = step1.run({})
    ok("marker without url -> fail",
       r["ok"] is False and "missing `url`" in r["error"])

    # 3. Happy path: session present with url + bundled embed tool reachable
    #    → calls embed (which writes public/charts/*.html in cwd) and
    #    returns a pause with View-in-dashboard.
    d = Path(tempfile.mkdtemp(prefix="show-")); tmps.append(d)
    (d / ".nilsson").mkdir(parents=True)
    (d / ".nilsson" / "run_local.json").write_text(json.dumps({
        "pid": os.getpid(), "url": "http://127.0.0.1:7700",
        "port": 7700, "start": ["python", "-V"],
    }))
    os.chdir(d)
    r = step1.run({})
    ok("happy -> pause", r.get("pause") is True)
    ok("happy -> View in dashboard link",
       "loadInDashboard" in r.get("detail_html", "")
       and "/public/charts/" in r.get("detail_html", ""))
    artifacts = list((d / "public" / "charts").glob("*.html"))
    ok("happy -> embed wrote a widget artifact", len(artifacts) == 1)

    # Active-marker is written so the chat UI can auto-load on reload.
    active = d / ".nilsson" / "dashboard_active.json"
    ok("happy -> dashboard_active.json written", active.exists())
    if active.exists():
        cfg = json.loads(active.read_text())
        ok("happy -> marker holds the dashboard widget URL",
           isinstance(cfg.get("url"), str) and "/public/charts/" in cfg["url"])
        ok("happy -> marker also records the project URL",
           cfg.get("project_url") == "http://127.0.0.1:7700")

    # 4. step_2: clean message AND clears the active marker (so reload
    #    after Stop does NOT auto-load anything).
    r = step2.run({})
    ok("step_2 ok message", r["ok"] and "Dashboard view ended" in r["output"])
    ok("step_2 removes dashboard_active.json", not active.exists())
    # Idempotent: calling step_2 again with no marker is fine.
    r = step2.run({})
    ok("step_2 no-marker -> still ok", r["ok"])
finally:
    os.chdir(orig_cwd)
    for d in tmps:
        shutil.rmtree(d, ignore_errors=True)

if fails:
    print(f"\n{len(fails)} failed: {fails}")
    sys.exit(1)
print("\nAll show_dashboard workflow tests passed.")
