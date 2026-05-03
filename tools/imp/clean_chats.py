#!/usr/bin/env python3
"""Delete chat history files and optionally execution logs.

Inputs:
  --include-logs: Also delete files in public/logs/ (default: off).
  --dry-run: List files that would be deleted without removing them.

Process: Scans .imp/chats/ (and optionally public/logs/) for files,
         deletes them, and reports a summary.
Output: Prints the count and paths of deleted (or to-be-deleted) files."""
import argparse
import os
import sys
from pathlib import Path

CHAT_DIR = Path(".imp/chats")
LOGS_DIR = Path("public/logs")


def _collect_entries(directory: Path) -> list[Path]:
    """Return all files and subdirectories in *directory*."""
    if not directory.is_dir():
        return []
    return sorted(directory.iterdir())


def main() -> int:
    parser = argparse.ArgumentParser(description="Clean up Imp chat history and logs")
    parser.add_argument(
        "--include-logs",
        action="store_true",
        help="Also delete execution logs in public/logs/",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting",
    )
    args = parser.parse_args()

    targets: dict[str, list[Path]] = {"chats": _collect_entries(CHAT_DIR)}
    if args.include_logs:
        targets["logs"] = _collect_entries(LOGS_DIR)

    total = 0
    for label, entries in targets.items():
        if not entries:
            print(f"{label}: nothing to clean")
            continue

        import shutil
        action = "would delete" if args.dry_run else "deleted"
        for entry in entries:
            if not args.dry_run:
                if entry.is_dir():
                    shutil.rmtree(entry)
                else:
                    entry.unlink()
            print(f"  {action}: {entry}")
        print(f"{label}: {action} {len(entries)} item(s)")
        total += len(entries)

    if total == 0:
        print("Nothing to clean up.")
    else:
        verb = "Would delete" if args.dry_run else "Deleted"
        print(f"\n{verb} {total} item(s) total.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
