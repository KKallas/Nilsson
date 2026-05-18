"""server/paths.py — single source of truth for directory paths.

Two directories matter:

- **NILSSON_DIR**: where Nilsson's code lives (server/, tools/, renderers/, etc.).
  Always the parent of this file's directory.

- **PROJECT_DIR**: where the project lives (.nilsson/, .git/, README, etc.).
  When developing Nilsson itself these are the same directory. When Nilsson is
  copied into a project as a subfolder, PROJECT_DIR is the project root
  and NILSSON_DIR is the subfolder.

nilsson.py sets the ``NILSSON_PROJECT_DIR`` env var when it detects it's being
run from a parent directory. If unset, PROJECT_DIR falls back to NILSSON_DIR.
"""

import os
from pathlib import Path

NILSSON_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = Path(os.environ.get("NILSSON_PROJECT_DIR", str(NILSSON_DIR)))
