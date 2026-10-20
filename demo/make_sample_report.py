"""Regenerate demo/sample-report from the synthetic history (deterministic).

    python demo/make_sample_report.py
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tool"))
sys.path.insert(0, str(ROOT / "demo"))

from generate_history import generate  # noqa: E402
from y2diag.cli import write_reports  # noqa: E402
from y2diag.config import load_config  # noqa: E402
from y2diag.pipeline import run_analysis  # noqa: E402
from y2diag.reports.build import findings  # noqa: E402

DEMO_NAME = "harborledger-demo"


def build(repo, out_dir):
    cfg = load_config(ROOT / "demo" / "config.yaml")
    res = run_analysis(repo, cfg, DEMO_NAME)
    written = write_reports(res, out_dir)
    lines = [f"Analyzed {res['meta']['commits']} commits. Findings:"]
    lines.extend(f"  - {item}" for item in findings(res))
    lines.append(f"Wrote {', '.join(written)}")
    (Path(out_dir) / "diagnostic-output.txt").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return res, sorted([*written, "diagnostic-output.txt"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", help="directory for the synthetic git history (default: a new temp dir)")
    args = parser.parse_args()
    repo = generate(args.repo)
    res, written = build(repo, ROOT / "demo" / "sample-report")
    print(f"Wrote {written} for {res['meta']['commits']} commits (repo in {repo})")
