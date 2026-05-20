"""Tests for tools/render/embed_project.py (issue #14).

Run: `python tests/test_embed_project.py`  (no pytest; exit 0 ok / 1 fail)

Covers the safety paths (no session, bad JSON, missing url) and the
happy path (valid session → artifact written, [Open in dashboard] link
printed, iframe src points at the session URL).
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Load as a fresh module so each test gets a clean import.
spec = importlib.util.spec_from_file_location(
    "_embed_project", ROOT / "tools" / "render" / "embed_project.py")
embed = importlib.util.module_from_spec(spec)
spec.loader.exec_module(embed)

fails: list[str] = []
tmps: list[Path] = []


def ok(name: str, cond: bool) -> None:
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name)


def run_in_tmp(session_payload: object | None) -> tuple[int, str, str, Path]:
    """chdir to a tmp PROJECT_DIR, optionally write a session marker,
    call main(['--port','8421']), return (rc, stdout, stderr, tmp)."""
    d = Path(tempfile.mkdtemp(prefix="embed-"))
    tmps.append(d)
    if session_payload is not None:
        (d / ".nilsson").mkdir(parents=True)
        (d / ".nilsson" / "run_local.json").write_text(
            session_payload if isinstance(session_payload, str)
            else json.dumps(session_payload))
    orig = Path.cwd()
    os.chdir(d)
    out, err = io.StringIO(), io.StringIO()
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = embed.main(["--port", "8421", "--title", "TestProject"])
    finally:
        os.chdir(orig)
    return rc, out.getvalue(), err.getvalue(), d


orig_cwd = Path.cwd()
try:
    # 1. No session marker → safe refusal, non-zero, clear message, NO artifact.
    rc, sout, serr, d = run_in_tmp(None)
    ok("no session → non-zero", rc != 0)
    ok("no session → clear message", "no project server" in serr.lower())
    ok("no session → no artifact written",
       not (d / "public" / "charts").exists())

    # 2. Bad JSON → non-zero, no artifact.
    rc, sout, serr, d = run_in_tmp("{not json")
    ok("bad JSON → non-zero", rc != 0)
    ok("bad JSON → no artifact", not (d / "public" / "charts").exists())

    # 3. Session without `url` → non-zero, clear message.
    rc, sout, serr, d = run_in_tmp({"pid": 123, "port": 7700})
    ok("no url → non-zero", rc != 0)
    ok("no url → mentions url",
       "url" in serr.lower())

    # 4. Happy path → artifact written, [Open in dashboard] printed,
    #    iframe src = session URL.
    sess_url = "http://192.168.1.5:7700"
    rc, sout, serr, d = run_in_tmp(
        {"pid": 42, "url": sess_url, "port": 7700})
    ok("happy → rc=0", rc == 0)
    ok("happy → [Open in dashboard] printed",
       "[Open in dashboard]" in sout)
    artifacts = list((d / "public" / "charts").glob("*.html"))
    ok("happy → artifact written", len(artifacts) == 1)
    if artifacts:
        html = artifacts[0].read_text()
        ok("happy → iframe src is session URL",
           f'src="{sess_url}"' in html)
        ok("happy → has Refresh button", "Refresh" in html and "f.src" in html)
        ok("happy → title escaped + present", "TestProject" in html)
        ok("happy → link printed points at the artifact",
           artifacts[0].name in sout)

    # 5. build_widget_html escapes hostile titles (no injection).
    html_ok = embed.build_widget_html(
        "https://x/", '"><script>bad</script>')
    ok("title HTML-escaped", "<script>bad" not in html_ok)
finally:
    os.chdir(orig_cwd)
    for d in tmps:
        shutil.rmtree(d, ignore_errors=True)

if fails:
    print(f"\n{len(fails)} failed: {fails}")
    sys.exit(1)
print("\nAll embed_project tests passed.")
