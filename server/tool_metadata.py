"""server/tool_metadata.py — in-file metadata-header contract for tools/workflows.

P1 of the tools-registry plan (see epic). Every tool/workflow can declare a
small metadata block; folder layout is no longer authoritative for *type*.

The block lives in the module docstring as ``Key: value`` lines, e.g.::

    \"\"\"Fetch open PRs and summarize them.

    Type: tool
    Canonical: false
    Origin: registry:tool/pr_digest@a1b2c3d
    ...
    \"\"\"

Equivalently, a top-level ``__nilsson__ = {...}`` dict literal is honored
(parsed via ``ast.literal_eval`` — no code execution).

Recognized keys:
  - ``Type``      — scene | controller | tool | workflow
  - ``Canonical`` — true/false; true => engine-coupled, excluded from
                    LLM auto-resolve in later phases
  - ``Origin``    — provenance string when pulled from the registry;
                    absent for locally-authored solutions

Parsing is deliberately tolerant: a missing/garbled header never raises —
the type is *inferred* instead (workflow if under ``workflows/`` or a
``step_*`` file exposing ``run(context)``, otherwise tool).
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

_VALID_TYPES = {"scene", "controller", "tool", "workflow"}
_TRUE = {"true", "1", "yes", "y", "on"}


@dataclass(frozen=True)
class ToolMeta:
    """Resolved metadata for a single tool/workflow file."""

    type: str  # one of _VALID_TYPES
    canonical: bool
    origin: Optional[str]
    inferred: bool  # True when type came from heuristics, not a header

    def as_dict(self) -> dict[str, object]:
        return {
            "type": self.type,
            "canonical": self.canonical,
            "origin": self.origin,
            "inferred": self.inferred,
        }


def _coerce_bool(value: str) -> bool:
    return value.strip().strip("'\"").lower() in _TRUE


def _parse_docstring_header(source: str) -> dict[str, str]:
    """Pull ``Key: value`` lines out of the module docstring.

    Only the recognized keys are returned; everything else (including the
    Inputs/Process/Output prose) is ignored.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {}
    doc = ast.get_docstring(tree) or ""
    found: dict[str, str] = {}
    for raw in doc.splitlines():
        line = raw.strip()
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip().lower()
        if key in ("type", "canonical", "origin") and key not in found:
            found[key] = val.strip()
    return found


def _parse_dunder(source: str) -> dict[str, str]:
    """Honor a top-level ``__nilsson__ = {...}`` literal, if present."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {}
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(t, ast.Name) and t.id == "__nilsson__" for t in node.targets
        ):
            continue
        try:
            data = ast.literal_eval(node.value)
        except (ValueError, SyntaxError):
            return {}
        if isinstance(data, dict):
            return {str(k).lower(): str(v) for k, v in data.items()}
    return {}


def _infer_type(path: Optional[Path], source: str) -> str:
    """Heuristic type when no header is declared."""
    if path is not None:
        parts = {p.lower() for p in path.parts}
        if "workflows" in parts:
            return "workflow"
        if path.name.startswith("step_"):
            return "workflow"
    try:
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "run":
                args = [a.arg for a in node.args.args]
                if args[:1] == ["context"] or args[:1] == ["ctx"]:
                    return "workflow"
    except SyntaxError:
        pass
    return "tool"


def parse_metadata(source: str, path: Optional[Path] = None) -> ToolMeta:
    """Resolve metadata for a tool/workflow file. Never raises.

    Precedence: ``__nilsson__`` dunder > docstring header > inference.
    """
    raw = _parse_docstring_header(source)
    raw.update({k: v for k, v in _parse_dunder(source).items() if v})

    declared_type = raw.get("type", "").strip().strip("'\"").lower()
    if declared_type in _VALID_TYPES:
        ttype, inferred = declared_type, False
    else:
        ttype, inferred = _infer_type(path, source), True

    canonical = _coerce_bool(raw["canonical"]) if "canonical" in raw else False
    origin = raw.get("origin", "").strip().strip("'\"") or None

    return ToolMeta(type=ttype, canonical=canonical, origin=origin, inferred=inferred)


def parse_file(path: Path) -> ToolMeta:
    """Convenience: read a file and parse its metadata. Never raises."""
    try:
        source = path.read_text(encoding="utf-8")
    except OSError:
        return ToolMeta(type="tool", canonical=False, origin=None, inferred=True)
    return parse_metadata(source, path)
