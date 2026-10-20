"""Configuration: a small YAML subset (maps, lists, scalars) or JSON. Stdlib only."""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Config:
    teams: dict = field(default_factory=dict)    # team -> [path prefixes]
    authors: dict = field(default_factory=dict)  # email glob -> team
    ignore: list = field(default_factory=list)
    paths: list = field(default_factory=list)
    since: str = None
    until: str = None
    max_commits: int = None
    max_files_per_commit: int = 30
    min_support: int = 5
    min_confidence: float = 0.5
    module_depth: int = 2
    top: int = 10
    bottleneck_min_teams: int = 3
    bottleneck_owner_share: float = 0.5
    small_team_authors: int = 3


_KEY = re.compile(r"""^("[^"]*"|'[^']*'|[^:]+?)\s*:(?:\s+(.*))?$""")


def _strip_comment(line):
    quote = None
    for i, ch in enumerate(line):
        if quote:
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
        elif ch == "#" and (i == 0 or line[i - 1] in " \t"):
            return line[:i]
    return line


def _scalar(text):
    text = text.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        return text[1:-1]
    if text.startswith("[") and text.endswith("]"):
        inner = text[1:-1].strip()
        return [_scalar(p) for p in inner.split(",")] if inner else []
    if text in ("null", "~", ""):
        return None
    if text in ("true", "false"):
        return text == "true"
    for cast in (int, float):
        try:
            return cast(text)
        except ValueError:
            pass
    return text


def _unquote_key(key):
    key = key.strip()
    if len(key) >= 2 and key[0] == key[-1] and key[0] in "\"'":
        return key[1:-1]
    return key


def _parse_block(items, i, indent):
    if items[i][1].startswith("- "):
        out = []
        while i < len(items) and items[i][0] == indent and items[i][1].startswith("- "):
            out.append(_scalar(items[i][1][2:]))
            i += 1
        return out, i
    out = {}
    while i < len(items) and items[i][0] == indent and not items[i][1].startswith("- "):
        m = _KEY.match(items[i][1])
        if not m:
            raise ValueError(f"cannot parse config line: {items[i][1]!r}")
        key, rest = _unquote_key(m.group(1)), (m.group(2) or "").strip()
        i += 1
        if rest:
            out[key] = _scalar(rest)
        elif i < len(items) and (
            items[i][0] > indent
            or (items[i][0] == indent and items[i][1].startswith("- "))
        ):
            out[key], i = _parse_block(items, i, items[i][0])
        else:
            out[key] = None
    return out, i


def parse_simple_yaml(text):
    items = []
    for raw in text.splitlines():
        line = _strip_comment(raw).rstrip()
        if line.strip():
            items.append((len(line) - len(line.lstrip(" ")), line.strip()))
    if not items:
        return {}
    data, _ = _parse_block(items, 0, items[0][0])
    return data


def load_config(path=None):
    cfg = Config()
    if path is None:
        return cfg
    text = Path(path).read_text(encoding="utf-8")
    data = json.loads(text) if str(path).endswith(".json") else parse_simple_yaml(text)
    for key, value in (data or {}).items():
        if not hasattr(cfg, key):
            raise ValueError(f"unknown config key: {key}")
        if value is None:
            continue
        setattr(cfg, key, value)
    cfg.teams = {t: ([p] if isinstance(p, str) else list(p or [])) for t, p in cfg.teams.items()}
    return cfg
