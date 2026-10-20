"""Map paths and authors to teams. CODEOWNERS is honoured when config has no rule."""

import fnmatch
import posixpath
from pathlib import Path

CODEOWNERS_LOCATIONS = ("CODEOWNERS", ".github/CODEOWNERS", "docs/CODEOWNERS")


def parse_codeowners(text):
    rules = []
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        parts = line.split()
        owners = [o for o in parts[1:] if o.startswith("@")]
        if owners:
            rules.append((parts[0], owners[0]))
    return rules


def load_codeowners(repo):
    for loc in CODEOWNERS_LOCATIONS:
        p = Path(repo) / loc
        if p.is_file():
            return parse_codeowners(p.read_text(encoding="utf-8", errors="replace"))
    return []


def _matches(pattern, path):
    anchored = pattern.startswith("/")
    p = pattern.lstrip("/")
    if p.endswith("/"):
        d = p.rstrip("/")
        if anchored or "/" in d:
            return path.startswith(d + "/")
        return d in path.split("/")[:-1]
    if "/" not in p and not anchored:
        return fnmatch.fnmatchcase(posixpath.basename(path), p)
    return fnmatch.fnmatchcase(path, p) or path.startswith(p + "/")


def owner_to_team(owner):
    return owner.lstrip("@").split("/")[-1]


class TeamResolver:
    def __init__(self, cfg, codeowners=()):
        self.cfg = cfg
        self.codeowners = list(codeowners)
        self._prefixes = sorted(
            ((p.lstrip("/"), team) for team, ps in cfg.teams.items() for p in ps),
            key=lambda pt: (-len(pt[0]), pt[0]),
        )
        self._cache = {}

    def team_of_path(self, path):
        if path in self._cache:
            return self._cache[path]
        team = None
        for prefix, t in self._prefixes:
            if path.startswith(prefix) if prefix.endswith("/") else (
                path == prefix or path.startswith(prefix + "/")
            ):
                team = t
                break
        if team is None:
            for pattern, owner in reversed(self.codeowners):  # last match wins
                if _matches(pattern, path):
                    team = owner_to_team(owner)
                    break
        self._cache[path] = team
        return team

    def team_of_author(self, email):
        for pattern, team in self.cfg.authors.items():
            if fnmatch.fnmatchcase(email.lower(), pattern.lower()):
                return team
        return "unmapped"

    def module_of(self, path):
        dirs = path.split("/")[:-1]
        if not dirs:
            return "(root)"
        return "/".join(dirs[: self.cfg.module_depth])
