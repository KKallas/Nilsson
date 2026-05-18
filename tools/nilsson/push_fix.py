#!/usr/bin/env python3
"""Push a bug fix from this project back to the upstream Nilsson repo as a PR.

Inputs:
  --files: str (repeatable) — files to push (relative paths, e.g. "server/render_route.py").
  --message: str — commit message / PR title.
  --repo: str — upstream Nilsson repo (default: read from .nilsson/upstream.json, or "KKallas/Imp").

Process:
  1. Clones the upstream Nilsson repo to a temp directory
  2. Copies the specified files from this project into the clone
  3. Creates a branch, commits, and pushes
  4. Opens a PR on the upstream repo

Output: Prints the PR URL."""

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PROJECT_DIR = Path(os.environ.get("NILSSON_PROJECT_DIR", str(ROOT)))
UPSTREAM_JSON = PROJECT_DIR / ".nilsson" / "upstream.json"

DEFAULT_REPO = "KKallas/Imp"


def run(cmd, **kwargs):
    return subprocess.run(cmd, capture_output=True, text=True, **kwargs)


def load_upstream_repo():
    """Read the upstream repo from .nilsson/upstream.json."""
    if UPSTREAM_JSON.exists():
        try:
            data = json.loads(UPSTREAM_JSON.read_text())
            if data.get("repo"):
                return data["repo"]
        except (json.JSONDecodeError, KeyError):
            pass
    return DEFAULT_REPO


def main() -> int:
    parser = argparse.ArgumentParser(description="Push a fix back to the upstream Nilsson repo")
    parser.add_argument("--files", action="append", required=True,
                        help="File to push (relative path, repeatable)")
    parser.add_argument("--message", required=True,
                        help="Commit message and PR title")
    parser.add_argument("--repo", default=None,
                        help="Upstream Nilsson repo (owner/name)")
    args = parser.parse_args()

    repo = args.repo or load_upstream_repo()

    # Validate files exist locally
    for f in args.files:
        local = ROOT / f
        if not local.exists():
            print(f"Error: {f} does not exist.", file=sys.stderr)
            return 1
        if not local.is_file():
            print(f"Error: {f} is not a file.", file=sys.stderr)
            return 1

    print(f"Upstream repo: {repo}")
    print(f"Files to push: {', '.join(args.files)}")
    print()

    # Clone upstream
    tmpdir = tempfile.mkdtemp(prefix="nilsson-pushfix-")
    try:
        print("Cloning upstream Nilsson repo...")
        result = run(["gh", "repo", "clone", repo, tmpdir])
        if result.returncode != 0:
            print(f"Error cloning: {result.stderr}", file=sys.stderr)
            return 1

        # Create branch
        slug = re.sub(r"[^a-z0-9]+", "-", args.message.lower())[:40].strip("-")
        branch = f"fix/{slug}"
        result = run(["git", "checkout", "-b", branch], cwd=tmpdir)
        if result.returncode != 0:
            print(f"Error creating branch: {result.stderr}", file=sys.stderr)
            return 1

        # Copy files
        for f in args.files:
            src = ROOT / f
            dest = Path(tmpdir) / f
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            print(f"  Copied: {f}")

        # Commit
        for f in args.files:
            run(["git", "add", f], cwd=tmpdir)
        result = run(["git", "commit", "-m", args.message], cwd=tmpdir)
        if result.returncode != 0:
            print(f"Error committing: {result.stderr}", file=sys.stderr)
            return 1

        # Push
        print("Pushing to upstream...")
        result = run(["git", "push", "-u", "origin", branch], cwd=tmpdir)
        if result.returncode != 0:
            print(f"Error pushing: {result.stderr}", file=sys.stderr)
            return 1

        # Create PR
        print("Creating PR...")
        result = run([
            "gh", "pr", "create",
            "--repo", repo,
            "--title", args.message,
            "--body", f"Bug fix pushed from a downstream project.\n\nFiles changed:\n"
                      + "\n".join(f"- `{f}`" for f in args.files),
            "--head", branch,
            "--base", "main",
        ], cwd=tmpdir)
        pr_url = result.stdout.strip()
        if result.returncode != 0:
            print(f"Error creating PR: {result.stderr}", file=sys.stderr)
            return 1
        if pr_url:
            print(f"\nPR: {pr_url}")

        print("Done.")

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
