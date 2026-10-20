"""Turn analysis results into neutral sections that Markdown and HTML renderers share."""

LIMITS_NOTE = (
    "Git history is a signal, not proof. This report is about modules and flows, "
    "not people: ownership is aggregated by team and must not be used to rate "
    "individuals or teams. See docs/limits.md."
)


def _pct(x):
    return f"{round(x * 100)}%"


def findings(res):
    out = []
    top = res["meta"]["top"]
    cross = [p for p in res["coupling"]["file_pairs"] if p["cross_module"]]
    if cross:
        p = cross[0]
        out.append(
            f"Strongest cross-module coupling: `{p['a']}` and `{p['b']}` changed together in "
            f"{p['support']} commits (confidence {p['confidence']})."
        )
    if res["hotspots"]["files"]:
        h = res["hotspots"]["files"][0]
        out.append(f"Top hotspot: `{h['path']}` (churn {h['churn']} x complexity {h['complexity']} = {h['score']}).")
    for m in res["ownership"]["modules"]:
        if m["bottleneck"]:
            out.append(
                f"Ownership bottleneck: `{m['module']}` is edited by {m['teams_touching']} teams, "
                f"and its owning team ({m['owner']}) authors only {_pct(m['owner_share'])} of the changes."
            )
    for a, b in res["dependencies"]["cycles"]:
        out.append(f"Mutual dependency (cycle) between `{a}` and `{b}`.")
    if not out:
        out.append("No coupling, hotspot, ownership or dependency signal crossed the configured thresholds.")
    return out


def build_sections(res):
    meta, top = res["meta"], res["meta"]["top"]
    sections = []

    sections.append({"title": "Summary", "paragraphs": [
        f"Analyzed **{meta['commits']}** commits ({meta['first_commit']} to {meta['last_commit']}). "
        f"Coupling threshold: support >= {meta['min_support']}, confidence >= {meta['min_confidence']}; "
        f"commits touching more than {meta['max_files_per_commit']} files are ignored for coupling and churn.",
        LIMITS_NOTE,
    ], "bullets": findings(res)})

    pairs = res["coupling"]["file_pairs"][:top]
    sections.append({
        "title": "Change coupling",
        "paragraphs": [
            "File pairs that change in the same commit. *Cross-module* pairs are the expensive ones: "
            "one change needs coordination between two places. Confidence = co-changes / commits of the less-changed file.",
        ],
        "table": {
            "headers": ["File A", "File B", "Co-changes", "Confidence", "Cross-module", "Cross-team"],
            "rows": [[p["a"], p["b"], p["support"], p["confidence"],
                      "yes" if p["cross_module"] else "no", "yes" if p["cross_team"] else "no"] for p in pairs],
        },
        "table2": {
            "caption": "Module pairs (commits touching both)",
            "headers": ["Module A", "Module B", "Commits", "Confidence"],
            "rows": [[p["a"], p["b"], p["support"], p["confidence"]] for p in res["coupling"]["module_pairs"][:top]],
        },
    })

    sections.append({
        "title": "Hotspots",
        "paragraphs": [
            "Churn (commits touching the file) multiplied by a simple complexity proxy "
            "(branch keywords + non-blank lines / 20). Frequently changed *and* hard to change is where risk concentrates.",
        ],
        "table": {
            "headers": ["File", "Team", "Churn", "LOC", "Branches", "Complexity", "Score"],
            "rows": [[h["path"], h["team"], h["churn"], h["loc"], h["branches"], h["complexity"], h["score"]]
                     for h in res["hotspots"]["files"][:top]],
        },
        "bars": [(h["path"], h["score"]) for h in res["hotspots"]["files"][:top]],
    })

    own = res["ownership"]
    sections.append({
        "title": "Ownership by team",
        "paragraphs": [
            "Counts are aggregated per team; individuals are never listed. A module edited by many teams, "
            "where the owning team authors a minority of changes, is a likely queue: changes wait for someone else's context or review.",
        ],
        "table": {
            "headers": ["Module", "Owner team", "Commits", "Teams touching", "Owner share", "Bottleneck"],
            "rows": [[m["module"], m["owner"], m["commits"], m["teams_touching"], _pct(m["owner_share"]),
                      "YES" if m["bottleneck"] else "no"] for m in own["modules"][:top]],
        },
        "table2": {
            "caption": "Teams",
            "headers": ["Team", "Commits authored", "Authors (count)", "Cross-team commit share",
                        "Inbound share on its files"],
            "rows": [[t["team"], t["commits_authored"],
                      f"{t['authors']}{' (small team: counts may identify people)' if t['small_team'] else ''}",
                      _pct(t["cross_team_commit_share"]), _pct(t["inbound_share"])] for t in own["teams"]],
        },
        "table3": {
            "caption": "Cross-team change flows (author team -> owning team)",
            "headers": ["From team", "To team", "Commits"],
            "rows": [[f["from"], f["to"], f["commits"]] for f in own["flows"][:top]],
        },
    })

    deps = res["dependencies"]
    sections.append({
        "title": "Dependency map",
        "paragraphs": [
            "Module-to-module imports found by static scanning (Python and JS/TS). Dashed arrows cross team boundaries. "
            "Mutual dependencies: " + (", ".join(f"`{a}` <-> `{b}`" for a, b in deps["cycles"]) or "none") + ".",
        ],
        "table": {
            "headers": ["From", "To", "Imports", "Cross-team", "Mutual"],
            "rows": [[e["src"], e["dst"], e["weight"], "yes" if e["cross_team"] else "no",
                      "yes" if e["mutual"] else "no"] for e in deps["edges"]],
        },
        "code": ("mermaid", res["dependency_mermaid"]),
    })
    return sections
