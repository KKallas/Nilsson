# Nilsson

An in-repo AI development helper. Nilsson lives inside your project and helps you build and maintain it — writing code, running reusable tools and workflows, rendering charts, and keeping the work under version control — all from a single web interface. Managing GitHub issues/PRs is one capability, not the whole point.

## Requirements

- Python 3.11 or newer
- [GitHub CLI (`gh`)](https://cli.github.com/) installed and authenticated (for the version-control / repo features)

## Setup

1. Copy the Nilsson folder into your project directory (or clone this repo)
2. Run:

```
python nilsson.py
```

3. Open http://127.0.0.1:8421 in your browser

On first run, Nilsson creates a virtual environment, installs dependencies, and starts the web server. No manual pip install needed.

The port is configurable with `RENDER_PORT`, and the project state directory with `NILSSON_PROJECT_DIR` — so you can run several independent single-user instances on one machine (each its own port + state, sharing the same code).

## First run

A setup wizard in the Chat tab guides you through:

- Checking if the folder is a git repository
- Connecting to GitHub via `gh` CLI
- Naming your project, picking a license, writing a README
- Creating a remote repo and pushing your files
- Setting up branch protection (require PR approval)

Other tabs (Queue, Workflows, Tools) are locked until setup completes.

## How it works

Nilsson is deliberately simple. No MCP servers, no complex protocols, no middleware.

```
Browser (HTML + JS)
    ↕ WebSocket
FastAPI server (render_route.py)
    ↕ claude-agent-sdk
Claude (with native Bash, Read, Write tools)
    ↕ subprocess
gh CLI, git, python scripts in tools/
```

Tools are plain Python scripts with argparse. Workflows are folders of numbered step scripts. Everything the agent does is a shell command or a file read/write — the same things you'd do manually in a terminal.

### Why no MCP

MCP adds a protocol layer between the agent and the tools. Nilsson doesn't need it — the agent already has Bash access. Keeping it simple means:

- Fewer moving parts to break
- Tools are just `.py` files you can run yourself
- No protocol versioning, no server lifecycle, **no tool registration** — a background scanner picks files up automatically
- Easy to debug: if a tool works in your terminal, it works in Nilsson

## The four tabs

### Queue

Your to-do list inside Nilsson. The agent or workflows push items here when something needs your attention — a PR to review, a decision, an approval. Each item has action buttons. A lightweight inbox: things land here, you deal with them, they disappear.

### Chat

A conversation with the agent (labelled **Nilsson**; your messages show as **You**). You say what you want done — "add a CLI flag to X", "summarize open bugs", "show me a burndown chart", "scaffold a parser" — and the agent picks which tools to run, writes code if needed, and streams results back.

**History**: every chat is saved to `.nilsson/chats/` as JSON. The sidebar lists past chats. Old chats can be turned into GitHub issues, or "productized" into reusable tools/workflows via the P button.

**Dashboard**: a collapsible panel on the right. Rendered charts/widgets appear here as interactive HTML. Click any chart image in the chat to open it in the dashboard.

**Snapshots**: the [+ Snapshot] button saves a named restore point — like a game save. Restore to any snapshot or turn one into a pull request. No git knowledge needed; Nilsson handles branches and commits.

### Tools

The idea: figure out how to do something by chatting with the agent, then convert it into a tool so it runs the exact same way every time — no LLM, no cost, no variation. A teammate runs the tool and gets the same result with zero effort.

A tool is a simple, fixed Python script that does one thing — a plain `.py` under `tools/<group>/<name>.py` with argparse and a docstring, runnable standalone. **No registration step**: a background scanner (`server/tool_watcher.py`) discovers new/changed/deleted files automatically (a broken or half-written file is skipped and logged, never breaking the others). A tool may declare an optional metadata header in its docstring:

```
Type: scene | controller | tool | workflow
Canonical: true | false                      # true => engine-coupled
Origin: registry:<type>/<name>@<commit>      # provenance, if pulled from a registry
```

Tools are grouped by folder (`github/`, `render/`, `llm/`, `nilsson/`, …); each group's README first line is shown to the agent. The Tools tab lets you browse, edit, test, and organize them, or ask the agent to generate new ones.

### Workflows

A workflow chains tools together with LLM glue between steps — interpreting results, making runtime decisions. Each workflow is a folder under `workflows/` with numbered step files (`step_1_sync.py`, …) passing a shared context forward. Workflows can pause mid-run for input (shown as a Queue item). Auto-discovered, same as tools.

Example: the `weekly_triage` workflow syncs issues, runs estimation heuristics, generates a burndown chart, and posts a summary — in one click.

## Direction

Nilsson is evolving toward general-purpose **modules** (data-backed cells with standard default pages — list / form / report — and declared interfaces, in the spirit of Odoo modules) so the same agent can build and maintain not just code but small data apps and hardware projects. Modules and the shared tools/workflows/interfaces registry are tracked in the project issues.

## License

MIT
