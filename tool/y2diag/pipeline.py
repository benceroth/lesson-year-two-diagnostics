"""Run all analyzers and return one plain-data result dict."""

from datetime import datetime, timezone
from pathlib import Path

from .analyzers import change_coupling, dependency_map, hotspots, ownership
from .gitlog import read_history
from .teams import TeamResolver, load_codeowners


def _day(ts):
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d")


def run_analysis(repo, cfg, name=None):
    repo = Path(repo).resolve()
    commits = read_history(repo, cfg.since, cfg.until, cfg.paths, cfg.ignore, cfg.max_commits)
    resolver = TeamResolver(cfg, load_codeowners(repo))
    deps = dependency_map.analyze(repo, resolver, cfg)
    stamps = [c.ts for c in commits]
    return {
        "meta": {
            "name": name or repo.name,
            "commits": len(commits),
            "first_commit": _day(min(stamps)) if stamps else None,
            "last_commit": _day(max(stamps)) if stamps else None,
            "teams_configured": sorted(set(cfg.teams) | {r[1].lstrip("@").split("/")[-1] for r in resolver.codeowners}),
            "max_files_per_commit": cfg.max_files_per_commit,
            "min_support": cfg.min_support,
            "min_confidence": cfg.min_confidence,
            "top": cfg.top,
        },
        "coupling": change_coupling.analyze(commits, resolver, cfg),
        "hotspots": hotspots.analyze(commits, resolver, cfg, repo),
        "ownership": ownership.analyze(commits, resolver, cfg),
        "dependencies": deps,
        "dependency_mermaid": dependency_map.to_mermaid(deps),
        "dependency_dot": dependency_map.to_dot(deps),
    }
