"""Regenerate demo/sample-report from the synthetic history (deterministic).

    python demo/make_sample_report.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tool"))
sys.path.insert(0, str(ROOT / "demo"))

from generate_history import generate  # noqa: E402
from y2diag.cli import write_reports  # noqa: E402
from y2diag.config import load_config  # noqa: E402
from y2diag.pipeline import run_analysis  # noqa: E402

DEMO_NAME = "harborledger-demo"


def build(repo, out_dir):
    cfg = load_config(ROOT / "demo" / "config.yaml")
    res = run_analysis(repo, cfg, DEMO_NAME)
    return res, write_reports(res, out_dir)


if __name__ == "__main__":
    repo = generate()
    res, written = build(repo, ROOT / "demo" / "sample-report")
    print(f"Wrote {written} for {res['meta']['commits']} commits (repo in {repo})")
