"""server/paths.py — single source of truth for directory paths.

Two directories matter:

- **IMP_DIR**: where Imp's code lives (server/, tools/, renderers/, etc.).
  Always the parent of this file's directory.

- **PROJECT_DIR**: where the project lives (.imp/, .git/, README, etc.).
  When developing Imp itself these are the same directory. When Imp is
  copied into a project as a subfolder, PROJECT_DIR is the project root
  and IMP_DIR is the subfolder.

imp.py sets the ``IMP_PROJECT_DIR`` env var when it detects it's being
run from a parent directory. If unset, PROJECT_DIR falls back to IMP_DIR.
"""

import os
from pathlib import Path

IMP_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = Path(os.environ.get("IMP_PROJECT_DIR", str(IMP_DIR)))
