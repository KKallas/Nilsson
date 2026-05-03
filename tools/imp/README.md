# imp

Local tools for managing the Imp project workspace.

## Tools

| Script | Purpose | Key Arguments |
|---|---|---|
| `clean_chats.py` | Delete chat history and execution logs | `--include-logs`, `--dry-run` |
| `list_tools.py` | List all available tool scripts | `--group`, `--verbose` |
| `make_tool.py` | Create GitHub issue + PR for a new tool | `--group`, `--name`, `--title` |
| `make_workflow.py` | Create GitHub issue + PR for a new workflow | `--name`, `--title` |

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
```
