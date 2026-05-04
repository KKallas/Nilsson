#!/usr/bin/env python3
"""Change the LLM backend configuration.

Inputs:
  --model: str    — model identifier (e.g. "moonshotai/kimi-k2").
  --base-url: str — API base URL (e.g. "https://openrouter.ai/api/v1").
  --api-key-env: str — env var name holding the API key (default: ANTHROPIC_API_KEY).
  --reset: flag   — remove custom LLM config and revert to Anthropic defaults.

Process: Writes the `llm` block in `.imp/config.json`. The Foreman agent
         reads this on next dispatch to configure the SDK client.
Output: Prints the updated LLM backend settings."""
import argparse
import json
import os
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_FILE = PROJECT_DIR / ".imp" / "config.json"


def _load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text())
        except json.JSONDecodeError:
            return {}
    return {}


def _save_config(cfg: dict) -> None:
    CONFIG_FILE.parent.mkdir(exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(description="Change the LLM backend")
    parser.add_argument("--model", help="Model identifier (e.g. moonshotai/kimi-k2)")
    parser.add_argument("--base-url", help="API base URL")
    parser.add_argument(
        "--api-key-env",
        default=None,
        help="Environment variable name for the API key (default: ANTHROPIC_API_KEY)",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Remove custom LLM config, revert to Anthropic defaults",
    )
    args = parser.parse_args()

    cfg = _load_config()

    if args.reset:
        cfg.pop("llm", None)
        _save_config(cfg)
        print("LLM backend reset to default (Anthropic).")
        print("Restart the chat or send a new message for changes to take effect.")
        return 0

    if not args.model and not args.base_url and not args.api_key_env:
        print("Nothing to change. Provide --model, --base-url, --api-key-env, or --reset.")
        return 1

    llm = cfg.get("llm", {})
    if args.model:
        llm["model"] = args.model
    if args.base_url:
        llm["base_url"] = args.base_url
    if args.api_key_env:
        llm["api_key_env"] = args.api_key_env

    # Warn if the API key env var is not set
    key_env = llm.get("api_key_env", "ANTHROPIC_API_KEY")
    if not os.environ.get(key_env):
        print(f"Warning: {key_env} is not set in the environment.", file=sys.stderr)
        print(f"The agent will fail until this variable is exported.", file=sys.stderr)

    cfg["llm"] = llm

    # Ensure the llm tool group is active so Foreman can discover it
    active = cfg.get("active_tools")
    if isinstance(active, list) and "llm" not in active:
        active.append("llm")

    _save_config(cfg)

    print("LLM backend updated:")
    print(f"  model:       {llm.get('model', '(SDK default)')}")
    print(f"  base_url:    {llm.get('base_url', 'https://api.anthropic.com')}")
    print(f"  api_key_env: {llm.get('api_key_env', 'ANTHROPIC_API_KEY')}")
    print()
    print("Restart the chat or send a new message for changes to take effect.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
