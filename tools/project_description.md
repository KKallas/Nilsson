# Project Description

This repository **is Nilsson** — an in-repo AI development helper. This file
is the project context the agent receives; when Nilsson is copied into
another project, replace it with that project's description.

## What Nilsson Is

A single-user web app you run inside a repo. It pairs a chat agent (Claude
via `claude-agent-sdk`) with a FastAPI server, a set of plain-Python tools
and step-based workflows, and a renderer/dashboard. The agent helps you
build and maintain the project while keeping work under version control and
reusing existing tools instead of reinventing them. GitHub issue/PR
management is one capability, not the whole purpose.

## Tech Stack

- Python 3.11+ backend, FastAPI (`server/render_route.py`), uvicorn
- `claude-agent-sdk` for the agent; native Bash/Read/Write tools, no MCP
- `gh` + `git` CLIs for version control / repo operations
- Plain-Python tools (`tools/<group>/*.py`) auto-discovered by a background
  scanner (`server/tool_watcher.py`) — no registration step
- Step-based workflows (`workflows/<name>/step_*.py`)
- Renderer plugins (`renderers/<name>/`) → HTML widgets in the dashboard

## Repository Structure

- `server/` — FastAPI app, agent bridge, guard, watcher, paths
- `tools/` — tool groups (see `tools/README.md`)
- `workflows/` — step-based workflows
- `renderers/` — dashboard renderer plugins
- `static/`, `chat.html` — the web UI
- `tests/` — standalone assert-based test scripts
- `nilsson.py` — entry point (venv bootstrap + uvicorn)

## Direction

Evolving toward general-purpose **modules** — data-backed cells with
standard default pages (list / form / report) and declared interfaces, in
the spirit of Odoo modules — plus a shared registry of tools/workflows/
interfaces. Tracked in the project issues.

## Key Paths

- `NILSSON_DIR` — where Nilsson's code lives (this repo / subfolder)
- `PROJECT_DIR` — where the consuming project lives (`NILSSON_PROJECT_DIR`
  env var; falls back to `NILSSON_DIR`)
- `RENDER_PORT` — server port (default 8421); set per instance to run
  multiple independent single-user instances on one machine
