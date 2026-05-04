# Imp

AI-powered project manager that lives inside your GitHub repo. Manage issues, run workflows, and chat with an AI agent — all from a single web interface.

## Requirements

- Python 3.11 or newer
- [GitHub CLI (`gh`)](https://cli.github.com/) installed and authenticated

## Setup

1. Copy the Imp folder into your project directory (or clone this repo)
2. Run:

```
python imp.py
```

3. Open http://127.0.0.1:8421 in your browser

That's it. On first run, Imp creates a virtual environment, installs dependencies, and starts the web server. No manual pip install needed.

## First run

When you open the browser for the first time, a setup wizard in the Chat tab guides you through:

- Checking if the folder is a git repository
- Connecting to GitHub via `gh` CLI
- Naming your project, picking a license, writing a README
- Creating a GitHub repo and pushing your files
- Setting up branch protection (require PR approval)

Other tabs (Queue, Workflows, Tools) are locked until setup completes. Once done, the full interface is available.

## How it works

Imp is deliberately simple. No MCP servers, no complex protocols, no middleware layers.

```
Browser (HTML + JS)
    ↕ WebSocket
FastAPI server (render_route.py)
    ↕ claude-agent-sdk
Claude (with native Bash, Read, Write tools)
    ↕ subprocess
gh CLI, git, python scripts in tools/
```

The agent talks to GitHub through `gh` commands. Tools are plain Python scripts with argparse. Workflows are folders of numbered step scripts. Everything the agent does is a shell command or a file read/write — the same things you'd do manually in a terminal.

### Why no MCP

MCP adds a protocol layer between the agent and the tools. Imp doesn't need it — the agent already has Bash access and can run any command directly. Keeping it simple means:

- Fewer moving parts to break
- Tools are just `.py` files you can run yourself
- No protocol versioning, no server lifecycle, no tool registration
- Easy to debug: if a tool works in your terminal, it works in Imp

## The four tabs

### Queue

Your to-do list inside Imp. The agent (or workflows) can push items here when something needs your attention — a PR to review, an issue to triage, a deploy to approve. Each item has action buttons so you can resolve it in one click. Think of it as a lightweight inbox: things land here, you deal with them, they disappear.

### Chat

A conversation with the AI agent (Foreman). You type what you want done — "list open bugs", "fix issue #12", "show me a burndown chart" — and the agent figures out which tools to run, writes code if needed, and streams the results back.

**History**: every chat is saved to `.imp/chats/` as JSON. The sidebar lists past chats so you can pick up where you left off. Old chats can be turned into GitHub issues before deleting, or "productized" into reusable tools and workflows via the P button.

**Dashboard**: a collapsible panel on the right side of the chat. When the agent renders a chart (burndown, kanban, scatter, etc.) it appears here as an interactive HTML widget. Click any chart image in the chat to open it in the dashboard.

**Snapshots**: the [+ Snapshot] button at the bottom of the chat saves a named restore point — like a game save. You can restore to any previous snapshot or turn one into a pull request. No git knowledge needed; Imp handles branches and commits behind the scenes.

### Tools

The idea: you figure out how to do something by chatting with the agent, then convert that into a tool so it runs the exact same way every time — no LLM, no cost, no variation. When another team member needs to do the same thing, they run the tool and get the same result with zero effort.

A tool is a simple, fixed Python script that does one thing. Plain `.py` files under `tools/<group>/<name>.py` — each has argparse, a docstring, and can be run standalone from the terminal. The agent discovers them automatically and can call any tool during a chat.

The Tools tab lets you browse, edit, test, and organize tools. You can also ask the agent to generate new tools from a description, or promote a one-off chat solution into a permanent tool via the P button.

Tools are grouped by folder (`github/`, `render/`, `imp/`, etc.). Each group can have a README and tools can have workflow step templates (`.step.py`) so they plug into workflows.

### Workflows

A workflow chains multiple tools together, with LLM glue in between. Where a tool is a single fixed script, a workflow is a sequence of tools that may need the AI agent to configure them, interpret results between steps, or make decisions at runtime — or both.

Each workflow is a folder under `workflows/` with numbered step files (`step_1_sync.py`, `step_2_heuristics.py`, …). Steps pass results forward through a shared context. Workflows can pause mid-run to ask for your input (the pause shows up as a Queue item).

You can build workflows from the UI by combining existing tools, or ask the agent to create one from a chat conversation.

Example: the `weekly_triage` workflow syncs GitHub issues, runs estimation heuristics, generates a burndown chart, and posts a summary — all in one click.

## License

MIT
