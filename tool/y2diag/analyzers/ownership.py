"""Ownership spread, aggregated by team. Individuals are never reported."""

from collections import Counter, defaultdict

UNMAPPED = "unmapped"


def analyze(commits, resolver, cfg):
    mods = defaultdict(lambda: {"commits": 0, "teams": Counter(), "authors": set(), "owners": Counter()})
    authored, team_authors = Counter(), defaultdict(set)
    cross, inbound, touched, flows = Counter(), Counter(), Counter(), Counter()

    for c in commits:
        files = set(c.files)
        if len(files) > cfg.max_files_per_commit:
            continue
        author_team = resolver.team_of_author(c.email)
        authored[author_team] += 1
        team_authors[author_team].add(c.email)
        modules, owners = set(), set()
        for f in files:
            m = resolver.module_of(f)
            modules.add(m)
            owner = resolver.team_of_path(f)
            mods[m]["owners"][owner or "unowned"] += 1
            if owner:
                owners.add(owner)
        for m in modules:
            mods[m]["commits"] += 1
            mods[m]["teams"][author_team] += 1
            mods[m]["authors"].add(c.email)
        touched.update(owners)
        if author_team != UNMAPPED:
            foreign = owners - {author_team}
            if foreign:
                cross[author_team] += 1
            for o in foreign:
                flows[(author_team, o)] += 1
                inbound[o] += 1

    modules_out = []
    for name, m in mods.items():
        owner = sorted(m["owners"].items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
        known = {t: n for t, n in m["teams"].items() if t != UNMAPPED}
        share = m["teams"][owner] / m["commits"] if m["commits"] else 0.0
        modules_out.append({
            "module": name, "owner": owner, "commits": m["commits"],
            "teams_touching": len(known), "authors": len(m["authors"]),
            "owner_share": round(share, 2),
            "by_team": dict(sorted(m["teams"].items())),
            "bottleneck": len(known) >= cfg.bottleneck_min_teams and share < cfg.bottleneck_owner_share,
        })
    modules_out.sort(key=lambda r: (not r["bottleneck"], r["owner_share"], r["module"]))

    teams_out = []
    for team in sorted(set(authored) | set(touched)):
        n_auth = len(team_authors.get(team, ()))
        teams_out.append({
            "team": team,
            "commits_authored": authored[team],
            "authors": n_auth,
            "small_team": 0 < n_auth < cfg.small_team_authors,
            "cross_team_commit_share": round(cross[team] / authored[team], 2) if authored[team] else 0.0,
            "commits_touching_its_files": touched[team],
            "inbound_share": round(inbound[team] / touched[team], 2) if touched[team] else 0.0,
        })
    teams_out.sort(key=lambda t: (-t["inbound_share"], t["team"]))

    flows_out = [{"from": a, "to": b, "commits": n}
                 for (a, b), n in sorted(flows.items(), key=lambda kv: (-kv[1], kv[0]))]
    return {"modules": modules_out, "teams": teams_out, "flows": flows_out}
