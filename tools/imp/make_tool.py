#!/usr/bin/env python3
"""Register a new tool locally.

Inputs:
  --group: str — tool group folder (e.g. "github", "render", "imp")
  --name: str — tool script name without .py (e.g. "deploy_checker")

Process:
  1. Verifies tools/<group>/<name>.py exists and is valid Python
  2. Reloads the Foreman tool list so the new tool is immediately available

Output: Prints confirmation. Use publish_pr.py to push to GitHub."""

import argparse
import ast
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent


def main():
    parser = argparse.ArgumentParser(description="Register a new tool locally")
    parser.add_argument("--group", required=True, help="Tool group folder (e.g. github, render)")
    parser.add_argument("--name", required=True, help="Tool name without .py (e.g. deploy_checker)")
    args = parser.parse_args()

    tool_path = ROOT / "tools" / args.group / f"{args.name}.py"
    if not tool_path.exists():
        print(f"Error: {tool_path.relative_to(ROOT)} does not exist.", file=sys.stderr)
        return 1

    # Validate syntax
    source = tool_path.read_text()
    try:
        ast.parse(source)
    except SyntaxError as e:
        print(f"Syntax error in {tool_path.relative_to(ROOT)}: {e}", file=sys.stderr)
        return 1

    # Extract docstring
    doc = ast.get_docstring(ast.parse(source)) or ""
    first_line = doc.split("\n")[0] if doc else "(no description)"

    # Reload Foreman prompt
    subprocess.run(
        [sys.executable, "tools/imp/reload_tools.py"],
        capture_output=True, cwd=str(ROOT),
    )

    print(f"Tool registered: tools/{args.group}/{args.name}.py")
    print(f"Description: {first_line}")
    print(f"\nTo publish to GitHub: python tools/imp/publish_pr.py --path tools/{args.group}/ --title \"...\"")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
