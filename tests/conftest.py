from __future__ import annotations

import pathlib
import sys

# Add project root to sys.path so "import src...." works in tests
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
