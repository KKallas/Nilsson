"""server/keystore.py — cross-platform secure credential storage.

Uses the ``keyring`` library which delegates to:
  - macOS:   Keychain
  - Windows: Windows Credential Manager
  - Linux:   Secret Service (GNOME Keyring / KDE Wallet) via D-Bus

All keys are stored under the service name ``imp``.
"""

from __future__ import annotations

SERVICE = "imp"


def get(name: str) -> str | None:
    """Retrieve a secret by name. Returns None if not stored."""
    try:
        import keyring
        return keyring.get_password(SERVICE, name)
    except Exception:
        return None


def set(name: str, value: str) -> None:
    """Store a secret by name."""
    import keyring
    keyring.set_password(SERVICE, name, value)


def delete(name: str) -> bool:
    """Delete a secret. Returns True if it existed."""
    try:
        import keyring
        keyring.delete_password(SERVICE, name)
        return True
    except Exception:
        return False
