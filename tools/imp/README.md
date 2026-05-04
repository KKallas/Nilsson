# imp

Local tools for managing the Imp project workspace.

## Tools

| Script | Purpose | Key Arguments |
|---|---|---|
| `clean_chats.py` | Delete chat history and execution logs | `--include-logs`, `--dry-run` |
| `list_tools.py` | List all available tool scripts | `--group`, `--verbose` |
| `make_tool.py` | Create GitHub issue + PR for a new tool | `--group`, `--name`, `--title` |
| `make_workflow.py` | Create GitHub issue + PR for a new workflow | `--name`, `--title` |
| `sync_upstream.py` | Pull latest Imp core updates into this project | `--dry-run`, `--repo` |
| `push_fix.py` | Push a bug fix back to the upstream Imp repo as a PR | `--files`, `--message`, `--repo` |

## Usage

```bash
# Preview what would be deleted
python tools/imp/clean_chats.py --dry-run

# Delete all chat history
python tools/imp/clean_chats.py

# Delete chat history AND execution logs
python tools/imp/clean_chats.py --include-logs

# Delete everything, preview first
python tools/imp/clean_chats.py --include-logs --dry-run

# List all tools
python tools/imp/list_tools.py

# List tools in a specific group
python tools/imp/list_tools.py --group github

# List all tools with descriptions
python tools/imp/list_tools.py --verbose

# Create a tool (after writing the .py file)
python tools/imp/make_tool.py --group github --name my_tool --title "Add my_tool"

# Create a workflow (after writing step files)
python tools/imp/make_workflow.py --name daily_report --title "Add daily report workflow"

# Check what Imp updates are available (no changes applied)
python tools/imp/sync_upstream.py --dry-run

# Pull latest Imp core updates
python tools/imp/sync_upstream.py

# Push a bug fix back to the Imp repo
python tools/imp/push_fix.py --files server/render_route.py --message "Fix WebSocket reconnect"

# Push multiple files
python tools/imp/push_fix.py --files server/render_route.py --files server/chat_ws.py --message "Fix chat reconnect"
```
