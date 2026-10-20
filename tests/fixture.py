import atexit
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for sub in ("tool", "demo", "tracing", "tracing/otel-demo"):
    sys.path.insert(0, str(ROOT / sub))

from generate_history import generate  # noqa: E402
from y2diag.config import load_config  # noqa: E402
from y2diag.pipeline import run_analysis  # noqa: E402

_cache = {}


def demo_repo():
    """Synthetic history in a temp dir (never inside this project); built once per test run."""
    if "repo" not in _cache:
        repo = generate()
        atexit.register(shutil.rmtree, repo.parent, True)
        _cache["repo"] = repo
    return _cache["repo"]


def demo_result():
    if "res" not in _cache:
        cfg = load_config(ROOT / "demo" / "config.yaml")
        _cache["res"] = run_analysis(demo_repo(), cfg, "harborledger-demo")
    return _cache["res"]
