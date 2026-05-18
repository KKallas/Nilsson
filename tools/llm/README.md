# LLM backend configuration

Tools for viewing and switching the LLM backend used by the Nilsson agent.

## Tools

| Script | Purpose | Key Arguments |
|---|---|---|
| `current.py` | Show the current LLM backend configuration | (none) |
| `change.py` | Change the LLM backend (model, base URL, API key) | `--model`, `--base-url`, `--api-key-env`, `--reset` |
| `options.py` | List known LLM backend presets | (none) |

## Usage

```bash
# Show current LLM backend
python tools/llm/current.py

# List available backend presets
python tools/llm/options.py

# Switch to Kimi K2 via OpenRouter
python tools/llm/change.py --model moonshotai/kimi-k2 --base-url https://openrouter.ai/api --api-key-env OPENROUTER_API_KEY

# Switch just the model
python tools/llm/change.py --model anthropic/claude-sonnet-4

# Revert to default Anthropic backend
python tools/llm/change.py --reset
```
