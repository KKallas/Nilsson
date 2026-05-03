#!/usr/bin/env python3
"""Create a GitHub issue and PR for a new Imp workflow.

Inputs:
  --name: str — workflow name (e.g. "daily_report")
  --title: str — human-readable title for the issue and PR
  --description: str — extended description (optional)

Process:
  1. Verifies workflows/<name>/ exists with step files
  2. Creates branch imp/wf-<name>
  3. Commits all changes under workflows/<name>/
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
    result = run(["git", "remote", "get-url", "origin"])
    if result.returncode == 0:
        url = result.stdout.strip()
        m = re.search(r"github\.com[:/](.+?)(?:\.git)?$", url)
        if m:
            return m.group(1)
    print("Error: could not determine repo. Set 'repo' in .imp/config.json.", file=sys.stderr)
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Create issue + PR for a new Imp workflow")
    parser.add_argument("--name", required=True, help="Workflow name (e.g. daily_report)")
    parser.add_argument("--title", required=True, help="Title for the issue and PR")
    parser.add_argument("--description", default="", help="Extended description")
    args = parser.parse_args()

    wf_dir = ROOT / "workflows" / args.name
    if not wf_dir.is_dir():
        print(f"Error: workflows/{args.name}/ does not exist.", file=sys.stderr)
        print("Write the workflow files first, then call make_workflow.py.", file=sys.stderr)
        return 1

    steps = list(wf_dir.glob("step_*.py"))
    if not steps:
        print(f"Error: workflows/{args.name}/ has no step files.", file=sys.stderr)
        return 1

    # Check we're on main
    result = run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    if result.stdout.strip() != "main":
        print(f"Error: must be on main branch (currently on {result.stdout.strip()}).", file=sys.stderr)
        return 1

    # Check for changes
    result = run(["git", "status", "--porcelain", "--", f"workflows/{args.name}/"])
    if not result.stdout.strip():
        print(f"No changes detected in workflows/{args.name}/.", file=sys.stderr)
        return 1

    repo = get_repo()
    branch = f"imp/wf-{args.name}"
    body = args.description or args.title

    print(f"Creating workflow PR for {args.name} ({len(steps)} steps)...")

    # Create branch
    result = run(["git", "checkout", "-b", branch])
    if result.returncode != 0:
        print(f"Error creating branch: {result.stderr}", file=sys.stderr)
        return 1

    # Stage workflow files
    run(["git", "add", f"workflows/{args.name}/"])

    # Commit
    result = run(["git", "commit", "-m", f"[WORKFLOW] {args.title}"])
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
        "--title", f"New workflow: {args.name}",
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
        "--title", f"[WORKFLOW] {args.title}",
        "--body", pr_body,
        "--head", branch,
        "--base", "main",
    ])
    if result.stdout.strip():
        print(f"PR: {result.stdout.strip()}")

    # Switch back to main, restore files so the workflow stays locally available
    wf_dir = f"workflows/{args.name}/"
    run(["git", "checkout", "main"])
    run(["git", "checkout", branch, "--", wf_dir])
    run(["git", "reset", "HEAD", wf_dir])

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
