"""Run the team queue failure-first scenario."""

import subprocess
import sys
from pathlib import Path

runner = Path(__file__).resolve().parents[1] / "run.py"
subprocess.run([sys.executable, str(runner), "team-queue"], check=True)
