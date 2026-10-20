import subprocess
import sys
import unittest
from pathlib import Path

import fixture


class FailureFirstTests(unittest.TestCase):
    def test_each_scenario_reports_its_planted_signal(self):
        script = Path(fixture.ROOT) / "break-it" / "run.py"
        result = subprocess.run(
            [sys.executable, str(script), "all"],
            cwd=fixture.ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        output = result.stdout
        self.assertIn("Caught cross-team coupling: invoice.py + export.py changed together 9 times", output)
        self.assertIn("Caught a team-dependency queue: src/shared is touched by 4 teams", output)
        self.assertIn("Caught the shared-database hotspot: database.py is", output)
        self.assertIn("Billing, Reporting and Identity", output)


if __name__ == "__main__":
    unittest.main()
