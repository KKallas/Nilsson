"""server/runtime.py — the headless execution runtime (issue #9).

This is what runs as the **project server** (the local project process when
target=local, or the box where the project is serviced remotely). It does
two things and nothing else:

  1. launches the project's own server  (descriptor ``start`` argv)
  2. runs Nilsson's **workflow/cron scheduler** for that project

It deliberately **never imports server.render_route** — no agent, no
admin, no tool/registry authoring surface. That exclusion *is* the
security boundary: the execution plane runs version-controlled automation
but offers no console to reconfigure itself or mint new tooling. Changing
what it does must go through the local control plane → PR.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from pathlib import Path

# Hard guard: the runtime must stay agent/admin-free. If render_route ever
# got imported into this process the security boundary would be gone.
assert "server.render_route" not in sys.modules, (
    "security: server.render_route must not be imported into the headless "
    "runtime — that would put the agent in the execution plane"
)


async def _run(spec, *, do_init: bool) -> int:
    proj_dir = Path(os.environ.get("NILSSON_PROJECT_DIR", str(Path.cwd())))

    if do_init and spec.init:
        print(f"[runtime] init: {' '.join(spec.init)}", file=sys.stderr)
        rc = subprocess.run(spec.init, cwd=proj_dir).returncode
        if rc != 0:
            print(f"[runtime] init failed (rc={rc})", file=sys.stderr)
            return rc

    print(f"[runtime] starting project server: {' '.join(spec.start)}",
          file=sys.stderr)
    proc = await asyncio.create_subprocess_exec(*spec.start, cwd=str(proj_dir))

    # Workflow/cron scheduler: resume anything interrupted, then idle —
    # this is the execution engine only, no authoring surface.
    try:
        import workflows
        if hasattr(workflows, "resume_paused_async"):
            await workflows.resume_paused_async()
        print("[runtime] workflow scheduler active", file=sys.stderr)
    except Exception as exc:                       # never block the server
        print(f"[runtime] workflow scheduler unavailable: {exc}",
              file=sys.stderr)

    rc = await proc.wait()
    print(f"[runtime] project server exited (rc={rc})", file=sys.stderr)
    return rc


def main(argv: list[str] | None = None) -> int:
    import argparse

    from server.project_server import load_project_server

    p = argparse.ArgumentParser(description="Nilsson headless project runtime")
    p.add_argument("--init", action="store_true",
                   help="run the project's one-time init before serving")
    args = p.parse_args(argv)

    res = load_project_server()
    if res.error:
        print(f"[runtime] bad project descriptor: {res.error}",
              file=sys.stderr)
        return 2
    if res.absent:
        print("[runtime] no `project` descriptor — nothing to run "
              "(this project has no separate server)", file=sys.stderr)
        return 0
    try:
        return asyncio.run(_run(res.spec, do_init=args.init))
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
