# tools/

Every tool Nilsson can run lives here. A tool is a plain Python script with
argparse and a docstring — runnable standalone from a terminal, and callable
by the agent during a chat.

## Layout

Tools are organized into **group folders**:

```
tools/
├── nilsson/    # workspace management (list/sync/publish/clean, watcher helpers)
├── github/     # issues, PRs, repos via the gh + git CLIs
├── render/     # wrappers that push charts/widgets to the dashboard
├── llm/        # view/switch the LLM backend
├── presets/    # save/load tool+workflow presets
├── remote/     # remote-trigger helpers
└── <group>/    # add your own
```

`project_description.md` holds the project context the agent receives.

## Auto-discovery — no registration

A background scanner (`server/tool_watcher.py`) polls `tools/` and
`workflows/` (~every 10 s). **Just drop a valid `.py` into a group folder**
and it becomes available within ~2 poll cycles — no `make_tool.py`,
`make_workflow.py`, or `reload_tools.py` call needed.

Two safety properties make "just drop a file" safe (they replace the
validation the old registration step did):

- a file that fails to parse is **skipped and logged** — it never breaks
  the prompt for the other tools;
- a file is only loaded once its size+mtime are **stable across two
  consecutive polls**, so a half-written file is never loaded mid-write.

Adding, changing, and deleting files are all picked up automatically.

## Optional metadata header

A tool/workflow may declare metadata in its module docstring (or an
equivalent top-level `__nilsson__ = {...}` literal):

```
Type: scene | controller | tool | workflow
Canonical: true | false                     # true => engine-coupled
Origin: registry:<type>/<name>@<commit>     # provenance, if pulled from a registry
```

Absent ⇒ the type is inferred (workflow if under `workflows/` or a
`step_*` file with `run(context)`, otherwise tool). See
`tools/nilsson/README.md` for the workspace tooling and
`server/tool_metadata.py` for the parser.

## How the agent uses tools

The system prompt tells the agent to **reuse before building**: check
workflows, then tools, then write Python, then raw Bash — in that order.
Each group's `README.md` first line is surfaced to the agent as the group
description, so keep it accurate.

## Conventions for a new tool

- shebang `#!/usr/bin/env python3`
- module docstring: one-line summary, then `Inputs:` / `Process:` / `Output:`
- `argparse` with clear `--flags`
- exit codes (`0` ok, non-zero on error); print machine-friendly output
- a matching `<name>.md` config file is optional (editable via the Tools tab)
- a `<name>.step.py` file makes the tool usable as a workflow step template

## Workflows

Workflows live in `workflows/<name>/` as numbered `step_*.py` files, each
exposing `def run(context): ...` and passing a shared context forward.
They are discovered by the same scanner.

## Legacy batch runner

`tools/run_all.sh` is a legacy budgeted batch runner for the `github/`
issue-automation scripts (`moderate_issues.py`, etc.). It predates the
chat/agent flow and is kept for non-interactive bulk runs; the normal path
is to ask the agent or run a workflow.
