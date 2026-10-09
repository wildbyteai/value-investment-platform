"""Fixed locations in the repository. Use these instead of counting ``Path(__file__).parents``."""
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_ROOT.parent
CONFIG_DIR = REPO_ROOT / 'config'
