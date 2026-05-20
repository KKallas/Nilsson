"""server/netguard.py — the control-plane binding invariant (issue #9).

Security model: the Nilsson control plane carries the agent + tool/admin
authoring surface. It must answer **loopback only** so a remote attacker
cannot reach it. The *project* server is a separate process and may bind
LAN/public — that is its own concern, not governed here.

`enforce_loopback()` is called right before the control server binds. It
**refuses to start** (loud, non-zero) on anything non-loopback —
especially ``0.0.0.0``, which would expose the agent to the network.

This is the ONLY core change for #9. Everything else is a tool/workflow.
The invariant must live in core because it has to fire *before* uvicorn
binds; tools/workflows run inside an already-started server, where it is
too late to refuse a bad bind.
"""

from __future__ import annotations

import sys

# Only these may host the control plane.
_LOOPBACK = frozenset({"127.0.0.1", "::1", "localhost", "::ffff:127.0.0.1"})


def is_loopback(host: str) -> bool:
    """True iff *host* is a loopback address/name (127.0.0.0/8, ::1, localhost)."""
    h = (host or "").strip().lower()
    if h in _LOOPBACK:
        return True
    # 127.0.0.0/8 (e.g. 127.0.1.1)
    parts = h.split(".")
    if len(parts) == 4 and parts[0] == "127" and all(
        p.isdigit() and 0 <= int(p) <= 255 for p in parts
    ):
        return True
    return False


def enforce_loopback(host: str, *, who: str = "Nilsson control plane") -> None:
    """Abort the process unless *host* is loopback.

    Call immediately before binding the control server. ``0.0.0.0`` and any
    routable address are rejected: the agent must never be network-exposed.
    """
    if is_loopback(host):
        return
    print(
        f"\n[SECURITY] Refusing to start: {who} would bind {host!r}, which is "
        f"not loopback.\nThe agent/authoring surface must answer local "
        f"requests only (127.0.0.1). Run the *project* server separately if "
        f"you need a network-facing service.\n",
        file=sys.stderr,
    )
    raise SystemExit(2)
