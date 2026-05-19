# nilsson

Local tools for managing the Nilsson project workspace.

## Auto-discovery (no registration)

The server auto-discovers tools and workflows via a background scanner
(`server/tool_watcher.py`). **Just drop a valid `.py` into a `tools/<group>/`
or `workflows/<name>/` folder** — it becomes available within ~2 poll
cycles (~20 s). No `make_tool.py` / `make_workflow.py` / `reload_tools.py`
call is needed; those scripts are now optional validation helpers only.

Two safety properties make this safe: a file that fails to parse is
skipped and logged (it never breaks the prompt for other tools), and a
file is only loaded once its size+mtime are stable across two consecutive
polls (a half-written file is never loaded mid-write).

### Metadata header (optional)

A tool/workflow may declare metadata in its module docstring:

```
Type: scene | controller | tool | workflow
Canonical: true | false      # true => engine-coupled
Origin: registry:<type>/<name>@<commit>   # provenance, if pulled from registry
```

Absent ⇒ the type is inferred (workflow if under `workflows/` or a
`step_*` file with `run(context)`, otherwise tool). A top-level
`__nilsson__ = {...}` dict literal is honored equivalently.

## Tools

| Script | Purpose | Key Arguments |
|---|---|---|
| `clean_chats.py` | Delete chat history and execution logs | `--include-logs`, `--dry-run` |
| `list_tools.py` | List all available tool scripts | `--group`, `--verbose` |
| `make_tool.py` | (Optional) validate a new tool + update group README | `--group`, `--name` |
| `make_workflow.py` | (Optional) validate a new workflow's steps | `--name` |
| `sync_upstream.py` | Pull latest Nilsson core updates into this project | `--dry-run`, `--repo` |
| `push_fix.py` | Push a bug fix back to the upstream Nilsson repo as a PR | `--files`, `--message`, `--repo` |

## Usage

```bash
# Preview what would be deleted
python tools/nilsson/clean_chats.py --dry-run

# Delete all chat history
python tools/nilsson/clean_chats.py

# Delete chat history AND execution logs
python tools/nilsson/clean_chats.py --include-logs

# Delete everything, preview first
python tools/nilsson/clean_chats.py --include-logs --dry-run

# List all tools
python tools/nilsson/list_tools.py

# List tools in a specific group
python tools/nilsson/list_tools.py --group github

# List all tools with descriptions
python tools/nilsson/list_tools.py --verbose

# (Optional) validate a tool after writing the .py file —
# the scanner already auto-loads it; this just checks syntax + README.
python tools/nilsson/make_tool.py --group github --name my_tool

# (Optional) validate a workflow's step files
python tools/nilsson/make_workflow.py --name daily_report

# Check what Nilsson updates are available (no changes applied)
python tools/nilsson/sync_upstream.py --dry-run

# Pull latest Nilsson core updates
python tools/nilsson/sync_upstream.py

# Push a bug fix back to the Nilsson repo
python tools/nilsson/push_fix.py --files server/render_route.py --message "Fix WebSocket reconnect"

# Push multiple files
python tools/nilsson/push_fix.py --files server/render_route.py --files server/chat_ws.py --message "Fix chat reconnect"
```
