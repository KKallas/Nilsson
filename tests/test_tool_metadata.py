"""Tests for server/tool_metadata.py.

Run directly: `python tests/test_tool_metadata.py`
No pytest. Asserts → exit 0 on success, exit 1 on failure.

Covers the in-file metadata header contract: docstring keys, the
__nilsson__ dunder (precedence + literal-only), and type inference
fallbacks when no header is declared. Parsing must never raise.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from server.tool_metadata import parse_metadata  # noqa: E402

failures: list[str] = []


def check(name: str, cond: bool) -> None:
    print(f"{'PASS' if cond else 'FAIL'}  {name}")
    if not cond:
        failures.append(name)


# 1. Full docstring header
src = '''"""Do a thing.

Type: scene
Canonical: true
Origin: registry:scene/foo@a1b2c3d

Inputs: --x
"""
'''
m = parse_metadata(src)
check("docstring type=scene", m.type == "scene")
check("docstring canonical=True", m.canonical is True)
check("docstring origin parsed", m.origin == "registry:scene/foo@a1b2c3d")
check("declared header not inferred", m.inferred is False)

# 2. Absent header on a plain tool -> inferred tool, no canonical, no origin
m = parse_metadata('"""Just a tool."""\nimport os\n')
check("absent -> tool", m.type == "tool")
check("absent -> inferred", m.inferred is True)
check("absent -> not canonical", m.canonical is False)
check("absent -> no origin", m.origin is None)

# 3. Inference: run(context) signature => workflow
m = parse_metadata('"""step."""\ndef run(context):\n    return {}\n')
check("run(context) -> workflow", m.type == "workflow")

# 4. Inference: path under workflows/ => workflow even without run()
m = parse_metadata('"""x"""\n', Path("workflows/daily/step_1.py"))
check("workflows/ path -> workflow", m.type == "workflow")

# 5. step_ filename => workflow
m = parse_metadata('"""x"""\n', Path("anything/step_init.py"))
check("step_ filename -> workflow", m.type == "workflow")

# 6. __nilsson__ dunder overrides docstring
src = '''"""Type: tool"""
__nilsson__ = {"Type": "controller", "Canonical": "true"}
'''
m = parse_metadata(src)
check("dunder overrides type", m.type == "controller")
check("dunder canonical", m.canonical is True)

# 7. Unknown declared type falls back to inference (not crash)
m = parse_metadata('"""Type: banana"""\ndef run(context):\n    pass\n')
check("invalid type -> inferred workflow", m.type == "workflow" and m.inferred)

# 8. Tolerant: a syntactically broken file must not raise
try:
    m = parse_metadata("def broken(:\n")
    check("syntax error tolerated", m.type == "tool")
except Exception as exc:  # noqa: BLE001
    check(f"syntax error tolerated (raised {exc!r})", False)

# 9. Non-literal __nilsson__ ignored (no code execution), falls back
m = parse_metadata('__nilsson__ = {"Type": some_fn()}\n"""x"""\n')
check("non-literal dunder ignored", m.type == "tool")

if failures:
    print(f"\n{len(failures)} failure(s): {failures}")
    sys.exit(1)
print("\nAll tool_metadata tests passed.")
