#!/usr/bin/env python3
"""List known LLM backend presets.

Inputs:
  (none)

Process: Prints a table of pre-configured backend options that work with
         the Claude Agent SDK's Anthropic-compatible API.
Output: Prints available backend presets with model, base URL, and notes."""
import sys


# Known working backends for the Claude Agent SDK
PRESETS = [
    {
        "name": "Anthropic (default)",
        "model": "(SDK default — Claude)",
        "base_url": "https://api.anthropic.com",
        "api_key_env": "ANTHROPIC_API_KEY",
        "notes": "Default. No config needed.",
    },
    {
        "name": "OpenRouter — Kimi K2",
        "model": "moonshotai/kimi-k2",
        "base_url": "https://openrouter.ai/api",
        "api_key_env": "OPENROUTER_API_KEY",
        "notes": "Anthropic-compatible. Set OPENROUTER_API_KEY.",
    },
    {
        "name": "OpenRouter — Claude Sonnet",
        "model": "anthropic/claude-sonnet-4",
        "base_url": "https://openrouter.ai/api",
        "api_key_env": "OPENROUTER_API_KEY",
        "notes": "Claude via OpenRouter.",
    },
    {
        "name": "OpenRouter — Claude Haiku",
        "model": "anthropic/claude-haiku-4",
        "base_url": "https://openrouter.ai/api",
        "api_key_env": "OPENROUTER_API_KEY",
        "notes": "Faster, cheaper Claude via OpenRouter.",
    },
]


def main() -> int:
    print("Known LLM backend presets:\n")
    for i, p in enumerate(PRESETS, 1):
        print(f"  {i}. {p['name']}")
        print(f"     model:       {p['model']}")
        print(f"     base_url:    {p['base_url']}")
        print(f"     api_key_env: {p['api_key_env']}")
        print(f"     notes:       {p['notes']}")
        print()

    print("To switch, run:")
    print("  python tools/llm/change.py --model <model> --base-url <url> --api-key-env <env_var>")
    print()
    print("To revert to defaults:")
    print("  python tools/llm/change.py --reset")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
