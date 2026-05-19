"""Tests for server/project_app_mount.py (issue #9, P0).

Run directly: `python tests/test_project_app_mount.py`
No pytest. Asserts → exit 0 on success, exit 1 on failure.

Verifies the project-app contract + the defensive loader: absence is not
an error, a syntax-broken or import-erroring project app degrades to "not
mounted" (never raises), the exactly-one-of router/app rule, MOUNT
validation incl. reserved-prefix collision, optional TITLE/background/
lifespan, the package form, and the env-var override. No fastapi needed —
the loader is duck-typed, so fixtures use plain objects.
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from server.project_app_mount import load_project_app, RESERVED_PREFIXES  # noqa: E402

fails: list[str] = []


def ok(name: str, cond: bool) -> None:
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name)


def with_dir():
    d = Path(tempfile.mkdtemp(prefix="pamount-"))
    return d


def write(d: Path, body: str, name: str = "project_app.py") -> Path:
    p = d / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body)
    return d


VALID_ROUTER = "class _R:\n    pass\nrouter = _R()\n"
VALID_APP = "class _A:\n    pass\napp = _A()\n"

tmpdirs: list[Path] = []


def D(body: str, name: str = "project_app.py") -> Path:
    d = with_dir()
    tmpdirs.append(d)
    write(d, body, name)
    return d


try:
    # 1. absent -> not ok, but error is None (absent is allowed)
    d = with_dir(); tmpdirs.append(d)
    r = load_project_app(d, log=False)
    ok("absent: not ok", not r.ok)
    ok("absent: error is None", r.error is None)

    # 2. syntax error -> rejected, never imported
    r = load_project_app(D("def broken(:\n"), log=False)
    ok("syntax error rejected", not r.ok and "SyntaxError" in (r.error or ""))

    # 3. neither router nor app
    r = load_project_app(D('"""nothing here"""\nX = 1\n'), log=False)
    ok("neither -> error", not r.ok and "exactly one" in (r.error or ""))

    # 4. both router and app
    r = load_project_app(D(VALID_ROUTER + VALID_APP), log=False)
    ok("both -> error", not r.ok and "exactly one" in (r.error or ""))

    # 5. router only, defaults
    r = load_project_app(D(VALID_ROUTER), log=False)
    ok("router loads", r.ok and r.app.kind == "router")
    ok("default mount /app", r.app and r.app.mount == "/app")
    ok("has a title", bool(r.app and r.app.title))

    # 6. app only
    r = load_project_app(D(VALID_APP), log=False)
    ok("app loads", r.ok and r.app.kind == "app")

    # 7. custom MOUNT + TITLE
    r = load_project_app(
        D(VALID_ROUTER + 'MOUNT = "/game"\nTITLE = "Mine"\n'), log=False)
    ok("custom mount", r.ok and r.app.mount == "/game")
    ok("custom title", r.ok and r.app.title == "Mine")

    # 8. invalid MOUNT "/"
    r = load_project_app(D(VALID_ROUTER + 'MOUNT = "/"\n'), log=False)
    ok("root mount rejected", not r.ok and "invalid MOUNT" in (r.error or ""))

    # 9. MOUNT without leading slash
    r = load_project_app(D(VALID_ROUTER + 'MOUNT = "app"\n'), log=False)
    ok("no-slash mount rejected", not r.ok and "invalid MOUNT" in (r.error or ""))

    # 10. reserved-prefix collision
    r = load_project_app(D(VALID_ROUTER + 'MOUNT = "/api"\n'), log=False)
    ok("reserved mount rejected", not r.ok and "reserved" in (r.error or ""))
    ok("reserved set sane", "api" in RESERVED_PREFIXES and "ws" in RESERVED_PREFIXES)

    # 11. import-time exception is caught (defensive — must not raise)
    raised = False
    try:
        r = load_project_app(
            D('raise RuntimeError("boom at import")\n'), log=False)
    except BaseException:                       # noqa: BLE001
        raised = True
    ok("import error not propagated", not raised)
    ok("import error reported", not r.ok and "import failed" in (r.error or ""))

    # 12. optional background / lifespan detected; bad background rejected
    r = load_project_app(
        D(VALID_ROUTER + "async def background():\n    pass\n"
          "class _L:\n    async def __aenter__(self): ...\n"
          "    async def __aexit__(self,*a): ...\n"
          "lifespan = _L()\n"), log=False)
    ok("background detected", r.ok and callable(r.app.background))
    ok("lifespan detected", r.ok and r.app.lifespan is not None)
    r = load_project_app(D(VALID_ROUTER + "background = 42\n"), log=False)
    ok("non-callable background rejected",
       not r.ok and "background" in (r.error or ""))

    # 13. package form: project_app/__init__.py
    d = with_dir(); tmpdirs.append(d)
    write(d, VALID_ROUTER, "project_app/__init__.py")
    r = load_project_app(d, log=False)
    ok("package form loads", r.ok and r.app.kind == "router")

    # 14. NILSSON_PROJECT_APP env override
    d = with_dir(); tmpdirs.append(d)
    write(d, VALID_APP, "custom_entry.py")
    os.environ["NILSSON_PROJECT_APP"] = "custom_entry.py"
    try:
        r = load_project_app(d, log=False)
    finally:
        del os.environ["NILSSON_PROJECT_APP"]
    ok("env override respected", r.ok and r.app.kind == "app")
finally:
    for d in tmpdirs:
        shutil.rmtree(d, ignore_errors=True)

if fails:
    print(f"\n{len(fails)} failed: {fails}")
    sys.exit(1)
print("\nAll project_app_mount tests passed.")
