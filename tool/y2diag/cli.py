import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .config import load_config
from .gitlog import GitError
from .pipeline import run_analysis
from .reports import render_html, render_markdown


def write_reports(res, out_dir, formats=("md", "html", "json")):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    files = {}
    if "md" in formats:
        files["report.md"] = render_markdown(res)
    if "html" in formats:
        files["report.html"] = render_html(res)
    if "json" in formats:
        public = {k: v for k, v in res.items() if k not in ("dependency_mermaid", "dependency_dot")}
        files["findings.json"] = json.dumps(public, indent=2, sort_keys=True) + "\n"
    files["dependencies.mmd"] = res["dependency_mermaid"]
    files["dependencies.dot"] = res["dependency_dot"]
    for name, text in files.items():
        with open(out / name, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
    return sorted(files)


def build_parser():
    p = argparse.ArgumentParser(prog="y2diag", description="Year-two architecture diagnostics from git history.")
    p.add_argument("--version", action="version", version=f"y2diag {__version__}")
    sub = p.add_subparsers(dest="command", required=True)
    a = sub.add_parser("analyze", help="analyze a git repository")
    a.add_argument("path")
    a.add_argument("--config", help="YAML/JSON config (see tool/config.example.yaml)")
    a.add_argument("--out", default="y2diag-report", help="output directory (default: y2diag-report)")
    a.add_argument("--since", help="only commits after this date (git syntax)")
    a.add_argument("--until")
    a.add_argument("--paths", nargs="*", help="limit history and scanning to these paths")
    a.add_argument("--max-commits", type=int)
    a.add_argument("--min-support", type=int)
    a.add_argument("--top", type=int)
    a.add_argument("--name", help="name shown in the report (default: folder name)")
    a.add_argument("--formats", default="md,html,json")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        cfg = load_config(args.config)
        for attr in ("since", "until", "paths", "max_commits", "min_support", "top"):
            value = getattr(args, attr)
            if value is not None:
                setattr(cfg, attr, value)
        res = run_analysis(args.path, cfg, args.name)
        written = write_reports(res, args.out, tuple(args.formats.split(",")))
    except (GitError, OSError, ValueError) as exc:
        print(f"y2diag: error: {exc}", file=sys.stderr)
        return 2
    from .reports.build import findings

    print(f"Analyzed {res['meta']['commits']} commits. Findings:")
    for f in findings(res):
        print(f"  - {f}")
    print(f"Wrote {', '.join(written)} to {args.out}")
    return 0
