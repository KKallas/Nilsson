#!/usr/bin/env python3
"""Publish a local tool or workflow to GitHub as an issue + PR.

Inputs:
  --path: str — path to tool group dir (e.g. "tools/imp/") or workflow dir (e.g. "workflows/daily_report/")
  --title: str — title for the issue and PR
  --description: str — extended description (optional)

Process:
  1. Detects uncommitted changes in the given path
  2. Creates a branch, commits, pushes
  3. Creates a GitHub issue and PR
  4. Switches back to main, keeps files locally

Output: Prints issue URL and PR URL."""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent


def run(cmd, **kwargs):
    """Run a command, return CompletedProcess."""
    return subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT), **kwargs)


def get_repo():
    """Read repo from .imp/config.json, fall back to git remote."""
    cfg = ROOT / ".imp" / "config.json"
    if cfg.exists():
        try:
            data = json.loads(cfg.read_text())
            if data.get("repo"):
                return data["repo"]
        except (json.JSONDecodeError, KeyError):
            pass
    result = run(["git", "remote", "get-url", "origin"])
    if result.returncode == 0:
        url = result.stdout.strip()
        m = re.search(r"github\.com[:/](.+?)(?:\.git)?$", url)
        if m:
            return m.group(1)
    print("Error: could not determine repo. Set 'repo' in .imp/config.json.", file=sys.stderr)
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Publish local tool/workflow as GitHub issue + PR")
    parser.add_argument("--path", required=True, help="Path to publish (e.g. tools/imp/ or workflows/daily_report/)")
    parser.add_argument("--title", required=True, help="Title for the issue and PR")
    parser.add_argument("--description", default="", help="Extended description")
    args = parser.parse_args()

    target = args.path.rstrip("/")
    full = ROOT / target
    if not full.exists():
        print(f"Error: {target} does not exist.", file=sys.stderr)
        return 1

    # Check we're on main
    result = run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    if result.stdout.strip() != "main":
        print(f"Error: must be on main branch (currently on {result.stdout.strip()}).", file=sys.stderr)
        return 1

    # Check for changes
    result = run(["git", "status", "--porcelain", "--", target])
    if not result.stdout.strip():
        print(f"No uncommitted changes in {target}.", file=sys.stderr)
        return 1

    repo = get_repo()
    # Branch name from path: tools/imp/foo -> imp/pub-imp-foo, workflows/bar -> imp/pub-bar
    slug = target.replace("/", "-").replace("tools-", "").replace("workflows-", "wf-")
    branch = f"imp/pub-{slug}"
    body = args.description or args.title

    print(f"Publishing {target}...")

    # Create branch
    result = run(["git", "checkout", "-b", branch])
    if result.returncode != 0:
        print(f"Error creating branch: {result.stderr}", file=sys.stderr)
        return 1

    # Stage and commit
    run(["git", "add", target])
    result = run(["git", "commit", "-m", args.title])
    if result.returncode != 0:
        print(f"Error committing: {result.stderr}", file=sys.stderr)
        run(["git", "checkout", "main"])
        return 1

    # Push
    result = run(["git", "push", "-u", "origin", branch])
    if result.returncode != 0:
        print(f"Error pushing: {result.stderr}", file=sys.stderr)
        run(["git", "checkout", "main"])
        return 1

    # Create issue
    result = run([
        "gh", "issue", "create",
        "--repo", repo,
        "--title", args.title,
        "--body", body,
    ])
    issue_url = result.stdout.strip()
    issue_num = ""
    if issue_url:
        m = re.search(r"/(\d+)$", issue_url)
        if m:
            issue_num = m.group(1)
        print(f"Issue: {issue_url}")

    # Create PR
    pr_body = f"Closes #{issue_num}\n\n{body}" if issue_num else body
    result = run([
        "gh", "pr", "create",
        "--repo", repo,
        "--title", args.title,
        "--body", pr_body,
        "--head", branch,
        "--base", "main",
    ])
    if result.stdout.strip():
        print(f"PR: {result.stdout.strip()}")

    # Switch back to main, restore files locally
    run(["git", "checkout", "main"])
    run(["git", "checkout", branch, "--", target])
    run(["git", "reset", "HEAD", target])

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
