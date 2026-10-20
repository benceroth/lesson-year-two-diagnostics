"""Static import scanning (Python, JS/TS) -> module-level dependency graph."""

import posixpath
import re
from collections import Counter
from pathlib import Path

from ..gitlog import tracked_files

PY_FROM = re.compile(r"^\s*from\s+(\.*)([\w.]*)\s+import\s+(.+)$")
PY_IMPORT = re.compile(r"^\s*import\s+([\w.,\s]+?)(?:\s+as\s+\w+)?\s*$")
JS_SPEC = re.compile(
    r"""(?:import\s+(?:[^'"]*?\sfrom\s+)?|export\s+[^'"]*?\sfrom\s+|require\(\s*)['"]([^'"]+)['"]"""
)
JS_EXTS = (".js", ".ts", ".jsx", ".tsx", ".mjs")


def _py_index(files):
    index = {}
    for f in files:
        if not f.endswith(".py"):
            continue
        parts = f[:-3].split("/")
        if parts[-1] == "__init__":
            parts = parts[:-1]
        for i in range(len(parts)):
            index.setdefault(".".join(parts[i:]), set()).add(f)
    return index


def _lookup(index, dotted, resolver):
    hits = index.get(dotted)
    if not hits:
        return None
    mods = {resolver.module_of(h) for h in hits}
    return sorted(hits)[0] if len(mods) == 1 else None


def _py_targets(path, text, index, fileset, resolver):
    out = []
    here = path.split("/")[:-1]
    for line in text.splitlines():
        m = PY_FROM.match(line)
        if m:
            dots, mod, names = m.groups()
            names = [n.strip().split(" as ")[0].strip() for n in names.strip("() \\").split(",")]
            names = [n for n in names if n.isidentifier()]
            if dots:
                base = here[: len(here) - (len(dots) - 1)] if len(dots) > 1 else here
                base = base + (mod.split(".") if mod else [])
                cands = ["/".join(base + [n]) for n in names] + ["/".join(base)]
                for cand in cands:
                    for suffix in (".py", "/__init__.py"):
                        if cand + suffix in fileset:
                            out.append(cand + suffix)
                            break
                    else:
                        continue
                    break
            else:
                for cand in [f"{mod}.{n}" for n in names] + [mod]:
                    hit = _lookup(index, cand, resolver)
                    if hit:
                        out.append(hit)
                        break
            continue
        m = PY_IMPORT.match(line)
        if m:
            for name in m.group(1).split(","):
                name = name.strip().split(" as ")[0].strip()
                parts = name.split(".")
                for k in range(len(parts), 0, -1):
                    hit = _lookup(index, ".".join(parts[:k]), resolver)
                    if hit:
                        out.append(hit)
                        break
    return out


def _js_targets(path, text, fileset):
    out = []
    for spec in JS_SPEC.findall(text):
        if not spec.startswith("."):
            continue
        base = posixpath.normpath(posixpath.join(posixpath.dirname(path), spec))
        options = [base] + [base + e for e in JS_EXTS] + [f"{base}/index{e}" for e in JS_EXTS]
        for o in options:
            if o in fileset:
                out.append(o)
                break
    return out


def analyze(repo, resolver, cfg):
    files = tracked_files(repo, cfg.paths, cfg.ignore)
    fileset = set(files)
    index = _py_index(files)
    edges, file_edges = Counter(), Counter()
    for f in files:
        ext = posixpath.splitext(f)[1]
        if ext != ".py" and ext not in JS_EXTS:
            continue
        try:
            text = (Path(repo) / f).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        targets = _py_targets(f, text, index, fileset, resolver) if ext == ".py" else _js_targets(f, text, fileset)
        for t in targets:
            a, b = resolver.module_of(f), resolver.module_of(t)
            if a != b:
                edges[(a, b)] += 1
                file_edges[(f, t)] += 1

    out_edges = []
    for (a, b), n in sorted(edges.items()):
        ta, tb = _module_team(a, resolver, files), _module_team(b, resolver, files)
        out_edges.append({
            "src": a, "dst": b, "weight": n,
            "cross_team": bool(ta and tb and ta != tb),
            "mutual": (b, a) in edges,
        })
    cycles = sorted({tuple(sorted((e["src"], e["dst"]))) for e in out_edges if e["mutual"]})
    nodes = sorted({e["src"] for e in out_edges} | {e["dst"] for e in out_edges})
    return {
        "nodes": nodes,
        "edges": out_edges,
        "cycles": [list(c) for c in cycles],
        "file_edges": [{"src": a, "dst": b, "count": n} for (a, b), n in sorted(file_edges.items())],
    }


def _module_team(module, resolver, files):
    votes = Counter(resolver.team_of_path(f) for f in files if resolver.module_of(f) == module)
    votes.pop(None, None)
    return sorted(votes.items(), key=lambda kv: (-kv[1], kv[0]))[0][0] if votes else None


def _node_id(name):
    return re.sub(r"\W", "_", name)


def to_mermaid(deps):
    lines = ["graph LR"]
    for n in deps["nodes"]:
        lines.append(f'  {_node_id(n)}["{n}"]')
    for e in deps["edges"]:
        arrow = "-.->" if e["cross_team"] else "-->"
        lines.append(f'  {_node_id(e["src"])} {arrow}|{e["weight"]}| {_node_id(e["dst"])}')
    return "\n".join(lines) + "\n"


def to_dot(deps):
    lines = ["digraph dependencies {", "  rankdir=LR;", "  node [shape=box];"]
    for n in deps["nodes"]:
        lines.append(f'  "{n}";')
    for e in deps["edges"]:
        style = ', style=dashed, color="#c0392b"' if e["mutual"] else (", style=dashed" if e["cross_team"] else "")
        lines.append(f'  "{e["src"]}" -> "{e["dst"]}" [label="{e["weight"]}"{style}];')
    lines.append("}")
    return "\n".join(lines) + "\n"
