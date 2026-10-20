"""Run the hidden coupling failure-first scenario."""

import subprocess
import sys
from pathlib import Path

runner = Path(__file__).resolve().parents[1] / "run.py"
subprocess.run([sys.executable, str(runner), "hidden-coupling"], check=True)
