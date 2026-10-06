"""Make the repository's ``src`` layout available to directly run test files."""

from pathlib import Path
import sys


SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src"
source_path = str(SOURCE_ROOT)
if source_path not in sys.path:
    sys.path.insert(0, source_path)
