import tempfile
import unittest
from pathlib import Path

import fixture  # noqa: F401
from render_breakdown import analyze, load_spans
from run_demo import run
from tracelib import format_traceparent, parse_traceparent


class TraceparentTests(unittest.TestCase):
    def test_roundtrip_and_invalid(self):
        tp = format_traceparent("a" * 32, "b" * 16)
        self.assertEqual(parse_traceparent(tp), ("a" * 32, "b" * 16))
        for bad in (None, "", "garbage", "00-" + "0" * 32 + "-" + "b" * 16 + "-01"):
            self.assertIsNone(parse_traceparent(bad))


class TracingDemoTests(unittest.TestCase):
    def run_demo(self, propagate):
        with tempfile.TemporaryDirectory() as d:
            path = run(propagate, Path(d) / "spans.jsonl", requests=5, concurrency=5)
            return analyze(load_spans(path))

    def test_propagation_reveals_hidden_queue_wait(self):
        res = self.run_demo(True)
        self.assertEqual(res["orphan_spans"], 0)
        worst = res["requests"][0]
        self.assertEqual(worst["services_seen"], ["billing", "identity", "notifications", "reporting"])
        reporting_wait = worst["cells"].get(("reporting", "wait (queue/backoff)"), 0)
        self.assertGreater(reporting_wait, 150)  # 5 concurrent, 80 ms single worker
        self.assertLess(worst["opaque_ms"], 1)

    def test_without_propagation_wait_is_opaque(self):
        res = self.run_demo(False)
        worst = res["requests"][0]
        self.assertEqual(worst["services_seen"], ["billing"])
        self.assertGreater(worst["opaque_ms"], 150)
        self.assertEqual(worst["cells"].get(("reporting", "wait (queue/backoff)"), 0), 0)
        self.assertGreater(res["orphan_spans"], 0)


if __name__ == "__main__":
    unittest.main()
