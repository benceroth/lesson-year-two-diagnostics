import contextlib
import io
import tempfile
import unittest
from pathlib import Path

import fixture
from make_sample_report import build
from y2diag.cli import main


def read(p):
    return Path(p).read_text(encoding="utf-8")


class ReportTests(unittest.TestCase):
    def test_sample_report_is_up_to_date_and_deterministic(self):
        committed = Path(fixture.ROOT) / "demo" / "sample-report"
        with tempfile.TemporaryDirectory() as d:
            _, written = build(fixture.demo_repo(), d)
            self.assertTrue(written)
            for name in written:
                self.assertEqual(read(Path(d) / name), read(committed / name), name)

    def test_dependency_svg_artifacts_match_generator(self):
        from render_dependency_graphs import main as render_graphs

        report = Path(fixture.ROOT) / "demo" / "sample-report"
        names = ("dependencies-before.svg", "dependencies-after.svg")
        committed = {name: read(report / name) for name in names}
        render_graphs()
        self.assertEqual(committed, {name: read(report / name) for name in names})
        self.assertIn("measured sample imports", committed[names[0]])
        self.assertIn("proposed async Reporting boundary", committed[names[1]])

    def test_no_personal_data_in_outputs(self):
        committed = Path(fixture.ROOT) / "demo" / "sample-report"
        for f in committed.iterdir():
            text = read(f)
            self.assertNotIn("example.test", text, f.name)
            self.assertNotIn("Dev 1", text, f.name)
            self.assertNotIn("Users", text, f.name)

    def test_cli_analyze(self):
        with tempfile.TemporaryDirectory() as d, contextlib.redirect_stdout(io.StringIO()) as out:
            code = main(["analyze", str(fixture.demo_repo()), "--config",
                         str(Path(fixture.ROOT) / "demo" / "config.yaml"), "--out", d, "--top", "3"])
            self.assertEqual(code, 0)
            self.assertIn("Ownership bottleneck", out.getvalue())
            self.assertTrue((Path(d) / "report.html").read_text(encoding="utf-8").startswith("<!doctype html>"))

    def test_cli_error_on_non_repo(self):
        with tempfile.TemporaryDirectory() as d, contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(["analyze", d, "--out", str(Path(d) / "out")]), 2)

    def test_time_window_filter(self):
        with tempfile.TemporaryDirectory() as d, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(["analyze", str(fixture.demo_repo()), "--since", "2030-01-01", "--out", d]), 0)
            self.assertIn("Analyzed **0** commits", read(Path(d) / "report.md"))


if __name__ == "__main__":
    unittest.main()
