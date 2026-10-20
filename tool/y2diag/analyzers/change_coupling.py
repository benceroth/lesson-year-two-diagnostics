"""Files and modules that change together (co-change in the same commit)."""

from collections import Counter
from itertools import combinations


def analyze(commits, resolver, cfg):
    file_n, pair_n, mod_n, modpair_n = Counter(), Counter(), Counter(), Counter()
    skipped = 0
    for c in commits:
        files = sorted(set(c.files))
        if len(files) > cfg.max_files_per_commit:
            skipped += 1  # mass renames/reformats say nothing about coupling
            continue
        file_n.update(files)
        pair_n.update(combinations(files, 2))
        mods = sorted({resolver.module_of(f) for f in files})
        mod_n.update(mods)
        modpair_n.update(combinations(mods, 2))

    pairs = []
    for (a, b), support in pair_n.items():
        confidence = support / min(file_n[a], file_n[b])
        if support < cfg.min_support or confidence < cfg.min_confidence:
            continue
        ta, tb = resolver.team_of_path(a), resolver.team_of_path(b)
        pairs.append({
            "a": a, "b": b, "support": support,
            "confidence": round(confidence, 2),
            "cross_module": resolver.module_of(a) != resolver.module_of(b),
            "cross_team": bool(ta and tb and ta != tb),
            "teams": [ta or "unowned", tb or "unowned"],
        })
    pairs.sort(key=lambda p: (not p["cross_module"], -p["support"], -p["confidence"], p["a"], p["b"]))

    module_pairs = []
    for (a, b), support in modpair_n.items():
        if support < cfg.min_support:
            continue
        module_pairs.append({
            "a": a, "b": b, "support": support,
            "confidence": round(support / min(mod_n[a], mod_n[b]), 2),
        })
    module_pairs.sort(key=lambda p: (-p["support"], -p["confidence"], p["a"], p["b"]))

    return {"file_pairs": pairs, "module_pairs": module_pairs, "skipped_large_commits": skipped}
