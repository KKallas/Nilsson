"""Tests for server/netguard.py (issue #9 — control-plane bind invariant)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from server.netguard import is_loopback, enforce_loopback  # noqa: E402

fails: list[str] = []


def ok(name: str, cond: bool) -> None:
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name)


for h in ("127.0.0.1", "localhost", "LOCALHOST", "::1", "127.0.1.1",
          "::ffff:127.0.0.1"):
    ok(f"loopback: {h}", is_loopback(h))

for h in ("0.0.0.0", "192.168.1.5", "10.0.0.1", "172.16.0.9",
          "example.com", "", "::"):
    ok(f"not loopback: {h!r}", not is_loopback(h))

try:
    enforce_loopback("127.0.0.1")
    ok("enforce allows loopback", True)
except SystemExit:
    ok("enforce allows loopback", False)

try:
    enforce_loopback("0.0.0.0")
    ok("enforce blocks 0.0.0.0", False)
except SystemExit as e:
    ok("enforce blocks 0.0.0.0", e.code != 0)

try:
    enforce_loopback("192.168.1.50")
    ok("enforce blocks LAN addr", False)
except SystemExit as e:
    ok("enforce blocks LAN addr", e.code != 0)

if fails:
    print(f"\n{len(fails)} failed: {fails}")
    sys.exit(1)
print("\nAll netguard tests passed.")
