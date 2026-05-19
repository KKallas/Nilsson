#!/usr/bin/env python3
"""Preview local working changes on the configured remote project server.

DEPRECATED?: no — this is the local→remote *preview* loop (issue #9). It
runs in the control plane (your machine). It does NOT deploy to production
— that is the git/PR flow. It just lets you *see* in-progress changes on
the remote before you decide to open a PR.

Inputs:
  --message: str — optional label for the preview snapshot.

Process:
  1. Captures the current working changes WITHOUT touching your branch or
     working tree (``git stash create`` → a dangling WIP commit; falls
     back to HEAD when the tree is clean).
  2. Force-pushes it to the remote ``preview`` branch.
  3. Invokes the descriptor's ``remote.sync`` hook (argv) so the remote
     checks out + restarts on that branch. If no hook is configured, prints
     the exact manual command instead.

Output: the preview branch + what the remote should run. The formal path
to production stays the normal PR — this never deploys."""

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(ROOT),
                           capture_output=True, text=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Preview changes on remote")
    parser.add_argument("--message", default="preview", help="snapshot label")
    args = parser.parse_args()

    sys.path.insert(0, str(ROOT))
    from server.project_server import load_project_server

    res = load_project_server()
    if res.error:
        print(f"Error: invalid project descriptor: {res.error}",
              file=sys.stderr)
        return 2
    if res.absent or not res.spec.remote_url:
        print("No remote configured (.nilsson/config.json -> "
              "project.remote.url). Preview targets a remote only.",
              file=sys.stderr)
        return 1
    spec = res.spec

    # Capture WIP without disturbing the branch/working tree.
    _git("add", "-A")
    created = _git("stash", "create", args.message)
    sha = created.stdout.strip()
    if not sha:                                  # clean tree → preview HEAD
        sha = _git("rev-parse", "HEAD").stdout.strip()
    if not sha:
        print("Error: not a git repo / nothing to preview.", file=sys.stderr)
        return 1

    push = _git("push", "-f", "origin", f"{sha}:refs/heads/preview")
    if push.returncode != 0:
        print(f"Error pushing preview branch: {push.stderr}", file=sys.stderr)
        return 1
    print(f"Pushed {sha[:8]} → origin/preview")

    if spec.remote_sync:
        print(f"Triggering remote sync: {' '.join(spec.remote_sync)}")
        rc = subprocess.run(spec.remote_sync).returncode
        if rc != 0:
            print(f"Remote sync hook exited rc={rc}", file=sys.stderr)
            return rc
        print(f"Preview live — see {spec.remote_url}")
    else:
        print("\nNo `remote.sync` hook configured. On the remote, run:")
        print("  git fetch origin && git checkout -B preview origin/preview "
              "&& <restart the project server>")
        print(f"Then view: {spec.remote_url}")
    print("\nThis is a preview only. Open a PR when you're happy.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
