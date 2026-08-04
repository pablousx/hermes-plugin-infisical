import os
import sys
from pathlib import Path

HERMES_REPO = Path(
    os.environ.get("HERMES_AGENT_REPO", Path.home() / ".hermes" / "hermes-agent")
).resolve()
if HERMES_REPO.exists():
    sys.path.insert(0, str(HERMES_REPO))

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
