"""Build short-lived synthetic git histories and run the real y2diag analyzers."""

import argparse
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tool"))
from y2diag.config import Config
from y2diag.pipeline import run_analysis
from y2diag.reports.build import findings

WORK = Path(__file__).resolve().parent / ".work"
TEAMS = {
    "billing": "src/billing/",
    "identity": "src/identity/",
    "reporting": "src/reporting/",
    "platform": "src/shared/",
}
AUTHORS = {f"{team}-*@example.test": team for team in TEAMS}
SCENARIOS = ("hidden-coupling", "team-queue", "shared-database-hotspot")


def _git(repo, *args, env=None):
    subprocess.run(["git", "-C", str(repo), *args], check=True, stdout=subprocess.DEVNULL,
                   stderr=subprocess.PIPE, env=env)


def _commit(repo, team, index, message):
    env = dict(os.environ)
    timestamp = 1_750_000_000 + index * 60
    env.update({
        "GIT_AUTHOR_NAME": "Scenario Example",
        "GIT_AUTHOR_EMAIL": f"{team}-demo@example.test",
        "GIT_COMMITTER_NAME": "Scenario Example",
        "GIT_COMMITTER_EMAIL": f"{team}-demo@example.test",
        "GIT_AUTHOR_DATE": f"{timestamp} +0000",
        "GIT_COMMITTER_DATE": f"{timestamp} +0000",
    })
    _git(repo, "add", "-A", env=env)
    _git(repo, "commit", "--quiet", "-m", message, env=env)


def _write(repo, rel, text):
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _new_repo(scenario):
    WORK.mkdir(parents=True, exist_ok=True)
    repo = WORK / f"{scenario}-{uuid.uuid4().hex}"
    repo.mkdir()
    _git(repo, "init", "--quiet", "--initial-branch=main")
    return repo


def _make_hidden_coupling(repo):
    invoice = "from src.reporting import export\n\ndef complete():\n    return export.build()\n"
    export = "from src.billing import invoice\n\ndef build():\n    return invoice.complete()\n"
    _write(repo, "src/billing/invoice.py", invoice)
    _write(repo, "src/reporting/export.py", export)
    _commit(repo, "billing", 0, "Create invoice flow")
    for i in range(1, 9):
        _write(repo, "src/billing/invoice.py", invoice + f"\n# change {i}\n")
        _write(repo, "src/reporting/export.py", export + f"\n# change {i}\n")
        _commit(repo, "reporting" if i % 2 else "billing", i, f"Change invoice and export {i}")


def _make_team_queue(repo):
    _write(repo, "src/shared/rules.py", "def calculate(value):\n    return value\n")
    _commit(repo, "platform", 0, "Create shared rules")
    teams = ("billing", "identity", "reporting")
    for i in range(1, 13):
        _write(repo, "src/shared/rules.py", f"def calculate(value):\n    # revision {i}\n    return value + {i}\n")
        _commit(repo, teams[(i - 1) % len(teams)], i, f"Adjust shared rule {i}")


def _make_shared_database(repo):
    database = (
        "def read_row(connection, key):\n"
        "    if connection is None: return None\n"
        "    if not key: return None\n"
        "    if isinstance(key, str): return connection.fetch(key)\n"
        "    if isinstance(key, int): return connection.fetch(str(key))\n"
        "    if key == 'invoice': return connection.fetch(key)\n"
        "    if key == 'export': return connection.fetch(key)\n"
        "    if key == 'account': return connection.fetch(key)\n"
        "    if key == 'payment': return connection.fetch(key)\n"
        "    if key == 'statement': return connection.fetch(key)\n"
        "    if key == 'notification': return connection.fetch(key)\n"
        "    if key == 'retry': return connection.fetch(key)\n"
        "    return None\n"
    )
    readers = {
        "src/billing/invoice.py": "from src.shared import database\ndef load_invoice(db, key):\n    return database.read_row(db, key)\n",
        "src/reporting/export.py": "from src.shared import database\ndef load_export(db, key):\n    return database.read_row(db, key)\n",
        "src/identity/authz.py": "from src.shared import database\ndef load_account(db, key):\n    return database.read_row(db, key)\n",
    }
    _write(repo, "src/shared/database.py", database)
    for path, text in readers.items():
        _write(repo, path, text)
    _commit(repo, "platform", 0, "Add shared database access")
    teams = ("billing", "reporting", "identity", "platform")
    paths = tuple(readers)
    for i in range(1, 17):
        _write(repo, "src/shared/database.py", database + f"\n# schema adjustment {i}\n")
        reader = paths[(i - 1) % len(paths)]
        _write(repo, reader, readers[reader] + f"\n# database consumer change {i}\n")
        _commit(repo, teams[(i - 1) % len(teams)], i, f"Change shared schema consumer {i}")


def _make_repo(repo, scenario):
    {"hidden-coupling": _make_hidden_coupling,
     "team-queue": _make_team_queue,
     "shared-database-hotspot": _make_shared_database}[scenario](repo)


def _config():
    return Config(
        teams={team: [prefix] for team, prefix in TEAMS.items()},
        authors=AUTHORS,
        min_support=3,
        min_confidence=0.5,
        module_depth=2,
        top=10,
        bottleneck_min_teams=3,
        bottleneck_owner_share=0.5,
    )


def analyze_scenario(scenario):
    if scenario not in SCENARIOS:
        raise ValueError(f"unknown scenario {scenario!r}; choose from {', '.join(SCENARIOS)}")
    repo = _new_repo(scenario)
    try:
        _make_repo(repo, scenario)
        result = run_analysis(repo, _config(), scenario)
        if scenario == "hidden-coupling":
            expected = {"src/billing/invoice.py", "src/reporting/export.py"}
            pair = next((p for p in result["coupling"]["file_pairs"] if {p["a"], p["b"]} == expected), None)
            if not pair or not pair["cross_module"] or not pair["cross_team"]:
                raise AssertionError("the cross-team invoice/export coupling was not reported")
            evidence = f"Caught cross-team coupling: invoice.py + export.py changed together {pair['support']} times."
        elif scenario == "team-queue":
            module = next((m for m in result["ownership"]["modules"] if m["module"] == "src/shared"), None)
            if not module or not module["bottleneck"]:
                raise AssertionError("the shared-module ownership bottleneck was not reported")
            evidence = (f"Caught a team-dependency queue: src/shared is touched by {module['teams_touching']} teams; "
                       f"owner share is {round(module['owner_share'] * 100)}%.")
        else:
            hotspot = next((h for h in result["hotspots"]["files"] if h["path"] == "src/shared/database.py"), None)
            sources = {e["src"] for e in result["dependencies"]["edges"] if e["dst"] == "src/shared"}
            expected = {"src/billing", "src/reporting", "src/identity"}
            if not hotspot or not expected.issubset(sources):
                raise AssertionError("shared database hotspot or consumer imports were not reported")
            evidence = (f"Caught the shared-database hotspot: database.py is {hotspot['churn']}-commit churn x "
                       f"complexity {hotspot['complexity']} (score {hotspot['score']}); "
                       "the dependency map shows Billing, Reporting and Identity importing src/shared.")
        return result, evidence
    finally:
        shutil.rmtree(repo, ignore_errors=True)
        try:
            WORK.rmdir()
        except OSError:
            pass


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run a failure-first y2diag scenario (no network or dependencies).")
    parser.add_argument("scenario", choices=(*SCENARIOS, "all"))
    args = parser.parse_args(argv)
    for scenario in SCENARIOS if args.scenario == "all" else (args.scenario,):
        result, evidence = analyze_scenario(scenario)
        print(f"\n{scenario}: {evidence}")
        print("Diagnostic findings:")
        for item in findings(result):
            print(f"  - {item}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
