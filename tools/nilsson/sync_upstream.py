#!/usr/bin/env python3
"""Pull latest Nilsson core updates into a project that has Nilsson copied in.

Inputs:
  --dry-run (flag): Show what would change without applying anything.
  --repo: str — upstream Nilsson repo (default: read from .nilsson/upstream.json, or "KKallas/Imp").

Process:
  1. Reads .nilsson/upstream.json for the last synced commit and core paths
  2. Downloads the latest Nilsson main branch to a temp directory
  3. Compares core files and shows a diff summary
  4. Applies changes (unless --dry-run)
  5. Updates .nilsson/upstream.json with the new commit hash

Output: Prints a summary of updated, added, and unchanged files."""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PROJECT_DIR = Path(os.environ.get("NILSSON_PROJECT_DIR", str(ROOT)))
UPSTREAM_JSON = PROJECT_DIR / ".nilsson" / "upstream.json"

DEFAULT_REPO = "KKallas/Imp"
DEFAULT_CORE_PATHS = [
    "server/",
    "pipeline/",
    "renderers/",
    "public/",
    "static/",
    "nilsson.py",
    "requirements.txt",
    "tools/__init__.py",
    "workflows/__init__.py",
    "tools/nilsson/",
    "tools/render/",
    "tools/presets/",
]


def run(cmd, **kwargs):
    return subprocess.run(cmd, capture_output=True, text=True, **kwargs)


def load_upstream_config():
    """Load .nilsson/upstream.json or return defaults."""
    if UPSTREAM_JSON.exists():
        try:
            return json.loads(UPSTREAM_JSON.read_text())
        except (json.JSONDecodeError, KeyError):
            pass
    return {
        "repo": DEFAULT_REPO,
        "commit": None,
        "synced_at": None,
        "core_paths": DEFAULT_CORE_PATHS,
    }


def save_upstream_config(config):
    UPSTREAM_JSON.parent.mkdir(parents=True, exist_ok=True)
    UPSTREAM_JSON.write_text(json.dumps(config, indent=2) + "\n")


def is_core_path(filepath, core_paths):
    """Check if a file path falls under one of the core paths."""
    for cp in core_paths:
        if cp.endswith("/"):
            if filepath.startswith(cp):
                return True
        else:
            if filepath == cp:
                return True
    return False


def collect_core_files(base_dir, core_paths):
    """Collect all files under core paths relative to base_dir."""
    files = {}
    for cp in core_paths:
        full = base_dir / cp
        if full.is_file():
            files[cp] = full.read_bytes()
        elif full.is_dir():
            for f in sorted(full.rglob("*")):
                if f.is_file():
                    rel = str(f.relative_to(base_dir))
                    files[rel] = f.read_bytes()
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description="Pull latest Nilsson core updates")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without applying")
    parser.add_argument("--repo", default=None, help="Upstream Nilsson repo (owner/name)")
    args = parser.parse_args()

    config = load_upstream_config()
    repo = args.repo or config.get("repo", DEFAULT_REPO)
    core_paths = config.get("core_paths", DEFAULT_CORE_PATHS)
    last_commit = config.get("commit")

    if last_commit:
        print(f"Last synced: {last_commit[:8]} ({config.get('synced_at', 'unknown')})")
    else:
        print("No previous sync recorded. Will do a full comparison.")

    print(f"Upstream: {repo}")
    print(f"Core paths: {len(core_paths)} entries")
    print()

    # Clone upstream to temp dir
    tmpdir = tempfile.mkdtemp(prefix="nilsson-sync-")
    try:
        print("Fetching latest Nilsson from GitHub...")
        result = run(
            ["gh", "repo", "clone", repo, tmpdir, "--", "--depth=1"],
        )
        if result.returncode != 0:
            print(f"Error cloning upstream: {result.stderr}", file=sys.stderr)
            return 1

        # Get the upstream HEAD commit
        result = run(["git", "rev-parse", "HEAD"], cwd=tmpdir)
        upstream_commit = result.stdout.strip()
        print(f"Upstream HEAD: {upstream_commit[:8]}")

        if upstream_commit == last_commit:
            print("\nAlready up to date.")
            return 0

        # Collect files from both sides
        upstream_files = collect_core_files(Path(tmpdir), core_paths)
        local_files = collect_core_files(ROOT, core_paths)

        # Compare
        updated = []
        added = []
        unchanged = []

        all_paths = sorted(set(upstream_files.keys()) | set(local_files.keys()))
        for path in all_paths:
            if path not in upstream_files:
                # File exists locally but not upstream — local addition, skip
                continue
            if path not in local_files:
                added.append(path)
            elif upstream_files[path] != local_files[path]:
                updated.append(path)
            else:
                unchanged.append(path)

        # Summary
        print(f"\n--- Sync summary ---")
        print(f"  Updated:   {len(updated)}")
        print(f"  Added:     {len(added)}")
        print(f"  Unchanged: {len(unchanged)}")

        if updated:
            print("\nFiles to update:")
            for f in updated:
                print(f"  M {f}")
        if added:
            print("\nFiles to add:")
            for f in added:
                print(f"  A {f}")

        if not updated and not added:
            print("\nNo core file changes to apply.")
            # Still update tracking
            if not args.dry_run:
                config["commit"] = upstream_commit
                config["synced_at"] = str(date.today())
                config["repo"] = repo
                save_upstream_config(config)
                print("Updated .nilsson/upstream.json")
            return 0

        if args.dry_run:
            print("\n(dry run — no changes applied)")
            return 0

        # Apply changes
        print("\nApplying changes...")
        for path in updated + added:
            dest = ROOT / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(upstream_files[path])
            print(f"  {'M' if path in updated else 'A'} {path}")

        # Update tracking
        config["commit"] = upstream_commit
        config["synced_at"] = str(date.today())
        config["repo"] = repo
        config["core_paths"] = core_paths
        save_upstream_config(config)
        print(f"\nDone. Synced to {upstream_commit[:8]}.")
        print("Review the changes, then commit when ready.")

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
