#!/usr/bin/env python3
"""Create a GitHub issue and PR for a new Imp tool.

Inputs:
  --group: str — tool group folder (e.g. "github", "render", "imp")
  --name: str — tool script name without .py (e.g. "deploy_checker")
  --title: str — human-readable title for the issue and PR
  --description: str — extended description (optional)

Process:
  1. Verifies tools/<group>/<name>.py exists
  2. Creates branch imp/tool-<name>
  3. Commits all changes under tools/<group>/
  4. Pushes and creates GitHub issue + PR
  5. Switches back to main

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
    # Fallback: parse git remote
    result = run(["git", "remote", "get-url", "origin"])
    if result.returncode == 0:
        url = result.stdout.strip()
        # https://github.com/OWNER/REPO.git or git@github.com:OWNER/REPO.git
        m = re.search(r"github\.com[:/](.+?)(?:\.git)?$", url)
        if m:
            return m.group(1)
    print("Error: could not determine repo. Set 'repo' in .imp/config.json.", file=sys.stderr)
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Create issue + PR for a new Imp tool")
    parser.add_argument("--group", required=True, help="Tool group folder (e.g. github, render)")
    parser.add_argument("--name", required=True, help="Tool name without .py (e.g. deploy_checker)")
    parser.add_argument("--title", required=True, help="Title for the issue and PR")
    parser.add_argument("--description", default="", help="Extended description")
    args = parser.parse_args()

    tool_path = ROOT / "tools" / args.group / f"{args.name}.py"
    if not tool_path.exists():
        print(f"Error: {tool_path.relative_to(ROOT)} does not exist.", file=sys.stderr)
        print("Write the tool file first, then call make_tool.py.", file=sys.stderr)
        return 1

    # Check we're on main
    result = run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    if result.stdout.strip() != "main":
        print(f"Error: must be on main branch (currently on {result.stdout.strip()}).", file=sys.stderr)
        return 1

    # Check for changes in the tool group directory
    result = run(["git", "status", "--porcelain", "--", f"tools/{args.group}/"])
    if not result.stdout.strip():
        print(f"No changes detected in tools/{args.group}/.", file=sys.stderr)
        return 1

    repo = get_repo()
    branch = f"imp/tool-{args.name}"
    body = args.description or args.title

    print(f"Creating tool PR for {args.group}/{args.name}...")

    # Create branch
    result = run(["git", "checkout", "-b", branch])
    if result.returncode != 0:
        print(f"Error creating branch: {result.stderr}", file=sys.stderr)
        return 1

    # Stage tool files
    run(["git", "add", f"tools/{args.group}/"])

    # Commit
    result = run(["git", "commit", "-m", f"[TOOL] {args.title}"])
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
        "--title", f"New tool: {args.group}/{args.name}",
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
        "--title", f"[TOOL] {args.title}",
        "--body", pr_body,
        "--head", branch,
        "--base", "main",
    ])
    if result.stdout.strip():
        print(f"PR: {result.stdout.strip()}")

    # Switch back to main, restore files so the tool stays locally available
    tool_dir = f"tools/{args.group}/"
    run(["git", "checkout", "main"])
    run(["git", "checkout", branch, "--", tool_dir])
    run(["git", "reset", "HEAD", tool_dir])

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
