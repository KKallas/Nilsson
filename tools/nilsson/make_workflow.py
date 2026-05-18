#!/usr/bin/env python3
"""Register a new workflow locally.

Inputs:
  --name: str — workflow name (e.g. "daily_report")

Process:
  1. Verifies workflows/<name>/ exists with step files
  2. Validates each step file has a run(context) function
  3. Reloads the Nilsson tool list

Output: Prints confirmation. Use publish_pr.py to push to GitHub."""

import argparse
import ast
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent


def main():
    parser = argparse.ArgumentParser(description="Register a new workflow locally")
    parser.add_argument("--name", required=True, help="Workflow name (e.g. daily_report)")
    args = parser.parse_args()

    wf_dir = ROOT / "workflows" / args.name
    if not wf_dir.is_dir():
        print(f"Error: workflows/{args.name}/ does not exist.", file=sys.stderr)
        return 1

    steps = sorted(wf_dir.glob("step_*.py"))
    if not steps:
        print(f"Error: workflows/{args.name}/ has no step files.", file=sys.stderr)
        return 1

    # Validate each step
    for step in steps:
        source = step.read_text()
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            print(f"Syntax error in {step.name}: {e}", file=sys.stderr)
            return 1
        has_run = any(
            isinstance(node, ast.FunctionDef) and node.name == "run"
            for node in ast.walk(tree)
        )
        if not has_run:
            print(f"Warning: {step.name} has no run(context) function.", file=sys.stderr)

    # Reload Nilsson prompt
    subprocess.run(
        [sys.executable, "tools/nilsson/reload_tools.py"],
        capture_output=True, cwd=str(ROOT),
    )

    print(f"Workflow registered: workflows/{args.name}/ ({len(steps)} steps)")
    for s in steps:
        doc = ast.get_docstring(ast.parse(s.read_text())) or "(no description)"
        print(f"  {s.name}: {doc.split(chr(10))[0]}")
    print(f"\nTo publish to GitHub: python tools/nilsson/publish_pr.py --path workflows/{args.name}/ --title \"...\"")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
