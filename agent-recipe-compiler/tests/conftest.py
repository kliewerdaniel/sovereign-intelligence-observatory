"""Agent Recipe Compiler test configuration."""

import sys
from pathlib import Path

COMPONENT = Path(__file__).resolve().parent.parent
if str(COMPONENT) not in sys.path:
    sys.path.insert(0, str(COMPONENT))
