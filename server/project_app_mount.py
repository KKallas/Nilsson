"""server/project_app_mount.py — load a project-supplied app (issue #9, P0).

The boundary model: Nilsson is the dev layer (agent, tools, git, admin);
the *project* is an app Nilsson **loads and serves** — like an installed
Odoo app. This module is P0: the contract + a defensive loader. It does
NOT wire anything into the server yet (that is P1).

## The project-app contract

A project may place a `project_app.py` (file) or `project_app/` (package)
in its ``PROJECT_DIR``. The filename is overridable with the
``NILSSON_PROJECT_APP`` env var. The module must define **exactly one** of:

  - ``router`` — a FastAPI ``APIRouter`` (preferred), or
  - ``app``    — an ASGI app (e.g. a FastAPI instance)

and may optionally define:

  - ``MOUNT``      — str, where to mount (default ``/app``). Must be a
                     single clean path segment and must not collide with
                     a Nilsson-reserved prefix.
  - ``TITLE``      — str, a human label (default: the module name).
  - ``background`` — ``async def background(): ...`` started as a task by
                     Nilsson and cancelled on shutdown (P1).
  - ``lifespan``   — an async context-manager (or zero-arg factory of one)
                     entered/exited around the server's lifetime (P1).

## Safety (same property as the P1 tool scanner)

Loading is defensive and **never raises into the server**:
  1. the source is ``ast.parse``-d first — a syntax-broken project app is
     rejected with a reason and never imported/executed;
  2. the import itself is guarded — any import-time exception is caught and
     turned into a reason.
A broken project app therefore degrades to "no app mounted", exactly like
a broken tool is skipped by ``server/tool_watcher.py`` — it can never take
the Nilsson server down with it.
"""

from __future__ import annotations

import ast
import importlib.util
import os
import re
import sys
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

DEFAULT_MOUNT = "/app"
_IMPORT_NAME = "nilsson_project_app"
_MOUNT_RE = re.compile(r"^/[a-z0-9][a-z0-9_-]*$")

# Top-level path segments Nilsson itself owns (see server/render_route.py).
RESERVED_PREFIXES = frozenset({
    "api", "render", "renderpng", "public", "static", "ws", "health",
})


@dataclass(frozen=True)
class ProjectApp:
    """A validated, importable project app — what P1 will mount."""

    module: Any                 # the imported module object
    kind: str                   # "router" | "app"
    target: Any                 # the APIRouter or ASGI app object
    mount: str                  # e.g. "/app"
    title: str
    background: Any | None      # async def or None
    lifespan: Any | None        # async cm / factory or None
    source: Path                # the file that was loaded


@dataclass(frozen=True)
class LoadResult:
    """Outcome of a load attempt. Never an exception — always this."""

    app: Optional[ProjectApp]
    error: Optional[str]        # human reason when app is None (None == "absent")

    @property
    def ok(self) -> bool:
        return self.app is not None


def _find_source(project_dir: Path) -> Optional[Path]:
    """Locate the project-app file: ``<name>.py`` or ``<name>/__init__.py``."""
    name = os.environ.get("NILSSON_PROJECT_APP", "project_app")
    if name.endswith(".py"):
        name = name[:-3]
    f = project_dir / f"{name}.py"
    if f.is_file():
        return f
    pkg = project_dir / name / "__init__.py"
    if pkg.is_file():
        return pkg
    return None


def _valid_target(obj: Any) -> bool:
    """Reject obviously-wrong exports (str/number/None) without needing
    fastapi imported — real type is duck-checked, kept dependency-light."""
    return obj is not None and not isinstance(
        obj, (str, bytes, int, float, bool, list, dict, tuple, set)
    )


def load_project_app(
    project_dir: Path | str | None = None, *, log: bool = True
) -> LoadResult:
    """Discover, defensively validate, and import the project app.

    Returns a :class:`LoadResult`. ``error`` is ``None`` when simply absent
    (a project need not ship an app), and a human string when something is
    present but unusable. This function never raises.
    """
    if project_dir is None:
        from server.paths import PROJECT_DIR as project_dir  # lazy
    project_dir = Path(project_dir)

    src = _find_source(project_dir)
    if src is None:
        return LoadResult(None, None)  # absent is not an error

    def fail(reason: str) -> LoadResult:
        if log:
            print(f"[project_app] not mounted: {reason} ({src})",
                  file=sys.stderr, flush=True)
        return LoadResult(None, reason)

    # 1. syntax gate — never import code that doesn't parse
    try:
        ast.parse(src.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, ValueError) as exc:
        return fail(f"{type(exc).__name__}: {exc}")

    # 2. guarded import — runtime import errors must not crash the server
    try:
        is_pkg = src.name == "__init__.py"
        spec = importlib.util.spec_from_file_location(
            _IMPORT_NAME, src,
            submodule_search_locations=[str(src.parent)] if is_pkg else None,
        )
        if spec is None or spec.loader is None:
            return fail("could not create import spec")
        module = importlib.util.module_from_spec(spec)
        added = str(project_dir) not in sys.path
        if added:
            sys.path.insert(0, str(project_dir))
        try:
            sys.modules[_IMPORT_NAME] = module
            spec.loader.exec_module(module)
        finally:
            if added:
                sys.path.remove(str(project_dir))
    except BaseException as exc:  # noqa: BLE001 — defensive by design
        sys.modules.pop(_IMPORT_NAME, None)
        return fail(f"import failed: {type(exc).__name__}: {exc}\n"
                    f"{traceback.format_exc(limit=3)}")

    # 3. contract validation
    router = getattr(module, "router", None)
    asgi = getattr(module, "app", None)
    if (router is None) == (asgi is None):
        return fail("must define exactly one of `router` or `app`")
    if router is not None and not _valid_target(router):
        return fail("`router` is not a router object")
    if asgi is not None and not _valid_target(asgi):
        return fail("`app` is not an ASGI app object")
    kind = "router" if router is not None else "app"
    target = router if router is not None else asgi

    mount = getattr(module, "MOUNT", DEFAULT_MOUNT)
    if not isinstance(mount, str) or not _MOUNT_RE.match(mount):
        return fail(f"invalid MOUNT {mount!r} — expected like '/app'")
    if mount.strip("/").split("/")[0] in RESERVED_PREFIXES:
        return fail(f"MOUNT {mount!r} collides with a reserved Nilsson prefix")

    title = getattr(module, "TITLE", None)
    if not isinstance(title, str) or not title.strip():
        title = _IMPORT_NAME if src.name != "__init__.py" else src.parent.name

    background = getattr(module, "background", None)
    if background is not None and not callable(background):
        return fail("`background` must be an async callable")
    lifespan = getattr(module, "lifespan", None)
    if lifespan is not None and not (
        callable(lifespan) or hasattr(lifespan, "__aenter__")
    ):
        return fail("`lifespan` must be an async context manager or factory")

    pa = ProjectApp(module=module, kind=kind, target=target, mount=mount,
                    title=title, background=background, lifespan=lifespan,
                    source=src)
    if log:
        print(f"[project_app] loaded {title!r} ({kind}) -> mount {mount}",
              file=sys.stderr, flush=True)
    return LoadResult(pa, None)
