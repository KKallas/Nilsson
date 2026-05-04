#!/usr/bin/env python3
"""Show the current LLM backend configuration.

Inputs:
  (none)

Process: Reads the `llm` block from `.imp/config.json` and prints the
         active model, base URL, and API key environment variable.
Output: Prints the current LLM backend settings, or 'default (Anthropic)'
        if no custom backend is configured."""
import json
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_FILE = PROJECT_DIR / ".imp" / "config.json"


def main() -> int:
    cfg: dict = {}
    if CONFIG_FILE.exists():
        try:
            cfg = json.loads(CONFIG_FILE.read_text())
        except json.JSONDecodeError:
            print("Error: could not parse .imp/config.json", file=sys.stderr)
            return 1

    llm = cfg.get("llm")
    if not llm:
        print("LLM backend: default (Anthropic)")
        print("  model:       (SDK default)")
        print("  base_url:    https://api.anthropic.com")
        print("  api_key_env: ANTHROPIC_API_KEY")
        return 0

    model = llm.get("model", "(SDK default)")
    base_url = llm.get("base_url", "https://api.anthropic.com")
    api_key_env = llm.get("api_key_env", "ANTHROPIC_API_KEY")

    print(f"LLM backend: custom")
    print(f"  model:       {model}")
    print(f"  base_url:    {base_url}")
    print(f"  api_key_env: {api_key_env}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
