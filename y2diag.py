"""Run without installing: python y2diag.py analyze <path>"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "tool"))

from y2diag.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
