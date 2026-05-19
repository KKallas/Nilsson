"""server/tool_watcher.py — defensive auto-scanner for tools/ and workflows/.

P1 of the tools-registry plan. Replaces the manual ``reload_tools.py`` /
``/api/reload-prompt`` push and the per-file registration step: drop a
``.py`` into a tool/workflow folder and it becomes available on its own.

Two safety properties make "just drop a file" safe, since this scanner
replaces the validation the old registration step performed:

  1. **ast.parse gate** — a syntactically broken (or half-written) file is
     skipped and logged; it never poisons the prompt for the other tools.
  2. **stat-twice debounce** — a path is only acted on when its
     ``(size, mtime)`` is identical across two consecutive polls, so a
     file still being written is never loaded mid-write.

A confirmed add / change / delete rebuilds the cached system prompt via
``server.nilsson_agent.reload_prompt`` — no manual reload needed.
"""

from __future__ import annotations

import ast
import asyncio
import sys
from pathlib import Path
from typing import Optional

_ROOT = Path(__file__).resolve().parent.parent
_WATCH_ROOTS = (_ROOT / "tools", _ROOT / "workflows")
DEFAULT_INTERVAL = 10.0


def _is_watched(path: Path) -> bool:
    """A real tool/workflow source file (not a package/template/cache)."""
    if path.suffix != ".py" or not path.is_file():
        return False
    if path.name.startswith("_") or path.name.endswith(".step.py"):
        return False
    if any(part.startswith((".", "__")) for part in path.parts):
        return False
    return True


def _snapshot(roots=_WATCH_ROOTS) -> dict[str, tuple[int, int]]:
    """Map each watched file -> (size_bytes, mtime_ns)."""
    snap: dict[str, tuple[int, int]] = {}
    for root in roots:
        if not root.is_dir():
            continue
        for p in root.rglob("*.py"):
            if not _is_watched(p):
                continue
            try:
                st = p.stat()
            except OSError:
                continue
            snap[str(p)] = (st.st_size, st.st_mtime_ns)
    return snap


def _loadable(path: str) -> tuple[bool, str]:
    """Return (ok, reason). ok=False means: exclude, don't crash."""
    try:
        src = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        return False, f"unreadable: {exc}"
    try:
        ast.parse(src)
    except SyntaxError as exc:
        return False, f"SyntaxError: {exc.msg} (line {exc.lineno})"
    return True, ""


def _log(msg: str) -> None:
    print(f"[tool_watcher] {msg}", file=sys.stderr, flush=True)


class ToolWatcher:
    """Polls the watch roots and reloads the prompt on confirmed changes."""

    def __init__(self, roots=_WATCH_ROOTS, reload_fn=None) -> None:
        # _prev: snapshot from the previous poll (for stability check)
        # _applied: state currently reflected in the prompt
        # _bad: paths already logged as unloadable (avoid log spam)
        self._roots = roots
        self._reload_fn = reload_fn or self._reload_prompt
        self._prev: dict[str, tuple[int, int]] = {}
        self._applied: dict[str, tuple[int, int]] = {}
        self._bad: set[str] = set()
        self._task: Optional[asyncio.Task] = None

    def prime(self) -> None:
        """Adopt the current on-disk state as already-applied.

        Called once at startup so steady state does not trigger a spurious
        reload one interval after boot. Loadable files are taken as the
        baseline; broken ones are logged and left out.
        """
        cur = _snapshot(self._roots)
        self._prev = cur
        for path, st in cur.items():
            ok, reason = _loadable(path)
            if ok:
                self._applied[path] = st
            else:
                self._bad.add(path)
                _log(f"skip (startup) {path}: {reason}")

    def poll_once(self) -> bool:
        """One scan. Returns True if a change was applied (prompt reloaded).

        Synchronous and side-effecting only on confirmed change — safe to
        call directly from tests.
        """
        cur = _snapshot(self._roots)
        prev = self._prev
        self._prev = cur

        effective = dict(self._applied)
        changed = False

        for path, st in cur.items():
            if prev.get(path) != st:
                continue  # not stable across two polls (or just appeared)
            ok, reason = _loadable(path)
            if ok:
                self._bad.discard(path)
                if effective.get(path) != st:
                    effective[path] = st
                    changed = True
            else:
                if path not in self._bad:
                    _log(f"skip {path}: {reason}")
                    self._bad.add(path)
                if path in effective:  # was good, now broken -> drop it
                    del effective[path]
                    changed = True

        # Deletions: gone for two consecutive polls.
        for path in list(effective):
            if path not in cur and path not in prev:
                del effective[path]
                self._bad.discard(path)
                changed = True

        if changed:
            n_add = len(set(effective) - set(self._applied))
            n_del = len(set(self._applied) - set(effective))
            self._applied = effective
            self._reload_fn()
            _log(
                f"applied changes (+{n_add} -{n_del}, "
                f"{len(effective)} active); prompt reloaded"
            )
        return changed

    @staticmethod
    def _reload_prompt() -> None:
        try:
            from server.nilsson_agent import reload_prompt

            reload_prompt()
        except Exception as exc:  # never let a reload failure kill the loop
            _log(f"reload_prompt failed: {exc}")

    async def _loop(self, interval: float) -> None:
        while True:
            await asyncio.sleep(interval)
            try:
                await asyncio.get_event_loop().run_in_executor(
                    None, self.poll_once
                )
            except Exception as exc:
                _log(f"poll failed: {exc}")

    def start(self, interval: float = DEFAULT_INTERVAL) -> asyncio.Task:
        """Prime baseline and launch the background poll loop."""
        self.prime()
        self._task = asyncio.create_task(self._loop(interval))
        _log(
            f"started (interval={interval:g}s, "
            f"{len(self._applied)} files baselined)"
        )
        return self._task


_watcher: Optional[ToolWatcher] = None


def start_watcher(interval: float = DEFAULT_INTERVAL) -> ToolWatcher:
    """Idempotently start the singleton watcher (called from server startup)."""
    global _watcher
    if _watcher is None:
        _watcher = ToolWatcher()
        _watcher.start(interval)
    return _watcher
