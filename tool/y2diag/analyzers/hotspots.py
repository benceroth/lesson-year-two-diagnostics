"""Hotspots: churn x a deliberately simple complexity proxy."""

import re
from collections import Counter
from pathlib import Path

CODE_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cs", ".java", ".go",
    ".rb", ".php", ".rs", ".kt", ".c", ".cc", ".cpp", ".h",
}
_BRANCH = re.compile(r"\b(?:if|elif|else\s+if|for|foreach|while|case|catch|except)\b|&&|\|\||\band\b|\bor\b")
MAX_BYTES = 1_000_000


def complexity(text):
    """branch keywords + non-blank lines / 20. A proxy, not cyclomatic complexity."""
    lines = [l for l in text.splitlines() if l.strip()]
    branches = sum(len(_BRANCH.findall(l)) for l in lines)
    return round(branches + len(lines) / 20, 1), len(lines), branches


def analyze(commits, resolver, cfg, repo):
    churn = Counter()
    for c in commits:
        files = set(c.files)
        if len(files) <= cfg.max_files_per_commit:
            churn.update(files)
    rows = []
    for path, n in churn.items():
        if Path(path).suffix.lower() not in CODE_EXTENSIONS:
            continue
        full = Path(repo) / path
        try:
            if not full.is_file() or full.stat().st_size > MAX_BYTES:
                continue
            text = full.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        cx, loc, branches = complexity(text)
        rows.append({
            "path": path, "module": resolver.module_of(path),
            "team": resolver.team_of_path(path) or "unowned",
            "churn": n, "loc": loc, "branches": branches,
            "complexity": cx, "score": round(n * cx, 1),
        })
    rows.sort(key=lambda r: (-r["score"], r["path"]))
    return {"files": rows}
