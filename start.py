#!/usr/bin/env python3
"""start.py — the one startup command (issue #9).

Runs both planes with the right security posture:

  * **control plane** — local Nilsson (agent/admin/authoring), loopback only.
    Always started (it's how you change anything).
  * **execution plane** — the project's *separate* server + workflow
    scheduler (server/runtime.py). Started **locally by default**. If the
    descriptor's ``target`` is ``remote`` it is NOT run here — instead we
    check the remote is up to date and point you at `preview`.

Local by default; remote is opt-in and never deployed from here (the
local→online path is the git/PR flow). The decision is a pure function
(`decide`) so it can be unit-tested without spawning anything.
"""

from __future__ import annotations

import os
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Plan:
    start_control: bool          # run local Nilsson (always True in practice)
    start_project_local: bool    # run the project server on this machine
    remote_check_url: str | None # if set, only health/freshness-check this
    note: str


def decide(res) -> Plan:
    """Pure: given a project-server load Result, decide what to launch.

    Control plane is always on. A broken or absent descriptor never blocks
    Nilsson itself — it just means no local project server.
    """
    if res.error:
        return Plan(True, False, None,
                    f"project descriptor invalid ({res.error}); "
                    f"control plane only")
    if res.absent:
        return Plan(True, False, None,
                    "no project server in this project; control plane only")
    spec = res.spec
    if spec.is_remote:
        return Plan(True, False, spec.remote_url,
                    f"target=remote: control plane local; project served at "
                    f"{spec.remote_url} (use `preview` to push changes)")
    return Plan(True, True, None,
                "target=local: control plane + project server, both local")


def _freshness(url: str) -> None:
    """Best-effort: is the remote reachable? (A full repo-HEAD compare is
    deferred — needs a remote /version endpoint; this just warns.)"""
    try:
        with urllib.request.urlopen(url, timeout=4) as r:
            print(f"[start] remote reachable: {url} (HTTP {r.status})")
    except (urllib.error.URLError, OSError) as exc:
        print(f"[start] WARNING: remote {url} unreachable: {exc}",
              file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    import argparse

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from server.project_server import load_project_server

    p = argparse.ArgumentParser(description="Start Nilsson + project server")
    p.add_argument("--plan", action="store_true",
                   help="print the launch plan and exit (no processes)")
    p.add_argument("--init", action="store_true",
                   help="run the project's one-time init first (local only)")
    args = p.parse_args(argv)

    plan = decide(load_project_server())
    print(f"[start] {plan.note}")
    if args.plan:
        print(f"[start] plan: control={plan.start_control} "
              f"project_local={plan.start_project_local} "
              f"remote_check={plan.remote_check_url}")
        return 0

    if plan.remote_check_url:
        _freshness(plan.remote_check_url)

    procs: list[subprocess.Popen] = []
    if plan.start_project_local:
        cmd = [sys.executable, "-m", "server.runtime"] + (
            ["--init"] if args.init else [])
        print("[start] launching project server (headless runtime)")
        procs.append(subprocess.Popen(cmd, cwd=str(ROOT)))

    # Control plane last, in the foreground — Ctrl+C stops everything.
    print("[start] launching Nilsson control plane (loopback)")
    try:
        rc = subprocess.call([sys.executable, str(ROOT / "nilsson.py")],
                             cwd=str(Path.cwd()))
    except KeyboardInterrupt:
        rc = 130
    finally:
        for pr in procs:
            pr.terminate()
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
