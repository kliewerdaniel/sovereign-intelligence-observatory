"""Root conftest: ensures shared infrastructure is importable."""

import sys
from pathlib import Path

ROOT = Path(__file__).parent
# Only add root directory so 'shared' module can be imported
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
