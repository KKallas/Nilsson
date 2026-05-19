#!/usr/bin/env python3
"""Validate a new tool locally (registration no longer required).

DEPRECATED: the server now auto-discovers tools via a background scanner
(server/tool_watcher.py) — just drop a valid .py into a tools/<group>/
folder and it becomes available within ~2 poll cycles. This script is kept
only as an optional syntax/README helper; it no longer "registers" anything.

Inputs:
  --group: str — tool group folder (e.g. "github", "render", "nilsson")
  --name: str — tool script name without .py (e.g. "deploy_checker")

Process:
  1. Verifies tools/<group>/<name>.py exists and is valid Python
  2. Updates the group README table (cosmetic only)

Output: Prints confirmation. Use publish_pr.py to push to GitHub."""

import argparse
import ast
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

    # Update group README with the new tool
    readme_path = ROOT / "tools" / args.group / "README.md"
    tree = ast.parse(source)
    tool_args = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(getattr(node, "func", None), ast.Attribute)
        and node.func.attr == "add_argument"
    ]
    arg_names = []
    for call in tool_args:
        for a in call.args:
            if isinstance(a, ast.Constant) and isinstance(a.value, str) and a.value.startswith("-"):
                arg_names.append(a.value)
    args_str = ", ".join(arg_names) if arg_names else "none"
    table_row = f"| `{args.name}.py` | {first_line} | {args_str} |"

    if readme_path.exists():
        content = readme_path.read_text()
        # Append row to existing table if it has one, skip if tool already listed
        if f"`{args.name}.py`" not in content:
            if "| Script |" in content or "|---|" in content:
                # Insert before the last blank line after the table
                lines = content.split("\n")
                insert_idx = len(lines)
                for i, line in enumerate(lines):
                    if ("|---|" in line or "| Script |" in line):
                        # Find end of table
                        for j in range(i + 1, len(lines)):
                            if not lines[j].strip().startswith("|"):
                                insert_idx = j
                                break
                        else:
                            insert_idx = len(lines)
                        break
                lines.insert(insert_idx, table_row)
                readme_path.write_text("\n".join(lines))
            else:
                # No table — append one
                content += f"\n\n## Tools\n\n| Script | Purpose | Key Arguments |\n|---|---|---|\n{table_row}\n"
                readme_path.write_text(content)
    else:
        # Create README
        readme_path.write_text(f"# {args.group}\n\n## Tools\n\n| Script | Purpose | Key Arguments |\n|---|---|---|\n{table_row}\n")

    # NOTE: no reload needed — server/tool_watcher.py auto-discovers this
    # file on its next poll. Registration is no longer a step.
    print(f"Tool validated: tools/{args.group}/{args.name}.py")
    print(f"Description: {first_line}")
    print(f"README updated: tools/{args.group}/README.md")
    print("Auto-discovered by the scanner — no registration/reload needed.")
    print(f"\nTo publish to GitHub: python tools/nilsson/publish_pr.py --path tools/{args.group}/ --title \"...\"")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
