"""Build a reproducible synthetic git history for the fictional HarborLedger codebase.

Planted patterns (the tests assert the analyzers find them):
  1. Change coupling: src/billing/invoice.py <-> src/reporting/export.py (cross-team).
     A weaker one: src/billing/invoice.py <-> src/identity/authz.py.
  2. Ownership bottleneck: src/billing/invoice.py is edited by every team; the owning
     team (billing) authors a minority of the changes.
  3. Hotspot: invoice.py gains a branch with almost every change.
  4. Dependency cycle: billing <-> reporting imports.
  5. Noise: one mass-reformat commit touching 40+ files (must not create coupling).

Everything is deterministic (fixed seed, fixed timestamps). The repo is written with
`git fast-import`, so it needs only the git CLI. Authors use example.test addresses.
"""

import argparse
import random
import subprocess
import sys
import tempfile
from pathlib import Path

SEED = 2024
START_TS = 1719792000  # 2024-07-01T00:00:00Z
END_TS = 1782864000    # 2026-07-01T00:00:00Z

TEAMS = ["billing", "identity", "reporting", "notifications", "platform"]
MODULE_DIR = {t: f"src/{t}" for t in TEAMS}
MODULE_DIR["platform"] = "src/shared"

FILES = {
    "billing": ["invoice.py", "payments.py", "ledger.py"],
    "identity": ["accounts.py", "authz.py", "session.py"],
    "reporting": ["export.py", "read_models.py", "schedule.py"],
    "notifications": ["channels.py", "retry.py", "templates.py"],
    "platform": ["config.py", "logging_utils.py"],
}
INVOICE = "src/billing/invoice.py"
EXPORT = "src/reporting/export.py"
AUTHZ = "src/identity/authz.py"

CODEOWNERS = """# Owners by capability (fictional)
/src/billing/ @harborledger/billing
/src/identity/ @harborledger/identity
/src/reporting/ @harborledger/reporting
/src/notifications/ @harborledger/notifications
/src/shared/ @harborledger/platform
"""

IMPORTS = {
    INVOICE: "from src.identity import authz\nfrom src.reporting import export\nfrom src.shared import config\n",
    "src/billing/payments.py": "from src.notifications import channels\n",
    "src/billing/ledger.py": "from src.shared import config\n",
    "src/reporting/export.py": "from src.billing import invoice\n",
    "src/reporting/read_models.py": "from src.billing import ledger\n",
    "src/notifications/retry.py": "from src.billing import invoice\n",
    "src/identity/session.py": "from src.shared import logging_utils\n",
}

INVOICE_BODY = (
    "\n\ndef complete_invoice(request, total):\n"
    "    if request is None:\n        return None\n"
    "    if request.get('draft') and not request.get('approved'):\n        total = 0\n"
)


def _email(team, k):
    return f"{team}-dev{k}@example.test"


def initial_files():
    files = {".github/CODEOWNERS": CODEOWNERS, "README.md": "# HarborLedger (synthetic demo history)\n"}
    for team, names in FILES.items():
        for name in names:
            path = f"{MODULE_DIR[team]}/{name}"
            body = f'"""{path}"""\n' + IMPORTS.get(path, "")
            if path == INVOICE:
                body += INVOICE_BODY
            files[path] = body
    for i in range(40):  # untouched stubs that a mass-reformat commit will sweep up
        files[f"src/shared/vendor/stub_{i:02d}.py"] = f'"""stub {i}"""\n'
    return files


def _append(path, content, n):
    if path == INVOICE:
        return content + f"    if rule_{n}:\n        total += {n}\n"
    return content + f"\n\ndef change_{n}(x):\n    return x + {n}\n"


def plan(rng):
    """Return a list of (author_team, [paths]) events in chronological order."""
    ev = []
    pick = lambda weights: rng.choices(list(weights), weights=list(weights.values()))[0]
    coupled_authors = {"billing": 8, "reporting": 12, "identity": 5, "notifications": 5}
    solo_invoice_authors = {"billing": 3, "identity": 3, "reporting": 3, "notifications": 3, "platform": 1}
    for _ in range(30):
        ev.append((pick(coupled_authors), [INVOICE, EXPORT]))
    for _ in range(14):
        ev.append((pick({"billing": 3, "identity": 5, "reporting": 2, "notifications": 2}), [INVOICE, AUTHZ]))
    for _ in range(40):
        ev.append((pick(solo_invoice_authors), [INVOICE]))
    for _ in range(14):
        ev.append(("billing" if rng.random() < 0.9 else "platform", [f"src/billing/{rng.choice(['payments.py', 'ledger.py'])}"]))
    for team in ["identity", "reporting", "notifications", "platform"]:
        own = [f"{MODULE_DIR[team]}/{n}" for n in FILES[team]]
        if team == "reporting":
            own = [p for p in own if p != EXPORT]
        if team == "identity":
            own = [p for p in own if p != AUTHZ]
        for _ in range(40):
            who = team if rng.random() < 0.92 else rng.choice([t for t in TEAMS if t != team])
            ev.append((who, [rng.choice(own)]))
        for _ in range(8):  # same-module pairs: coupling that is not a boundary problem
            ev.append((team, rng.sample(own, 2)))
    rng.shuffle(ev)
    ev.insert(len(ev) // 2, ("platform", None))  # None => mass reformat
    return ev


def build_stream(files):
    rng = random.Random(SEED)
    events = plan(rng)
    out = bytearray()
    state = dict(files)

    def commit(ts, team, k, message, changes):
        name = f"{team.title()} Dev {k}"
        out.extend(f"commit refs/heads/main\ncommitter {name} <{_email(team, k)}> {ts} +0000\n".encode())
        msg = message.encode()
        out.extend(f"data {len(msg)}\n".encode() + msg + b"\n")
        for path, content in changes.items():
            data = content.encode()
            out.extend(f"M 100644 inline {path}\ndata {len(data)}\n".encode() + data + b"\n")
        out.extend(b"\n")

    commit(START_TS, "platform", 1, "Initial commit", state)
    step = (END_TS - START_TS) // (len(events) + 1)
    for i, (team, paths) in enumerate(events, start=1):
        ts = START_TS + i * step + rng.randrange(0, 3600)
        k = rng.randint(1, 3)
        if paths is None:
            changes = {p: c + "# reformatted\n" for p, c in state.items() if p.endswith(".py")}
            msg = "Reformat all python files"
        else:
            changes = {p: _append(p, state[p], i) for p in paths}
            msg = f"Change {', '.join(Path(p).name for p in paths)} (#{i})"
        state.update(changes)
        commit(ts, team, k, msg, changes)
    return bytes(out)


def generate(dest=None):
    """Create the repo at dest (default: a new temp dir). Returns its Path."""
    if dest is None:
        dest = Path(tempfile.mkdtemp(prefix="y2diag-")) / "harborledger-demo"
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    git = ["git", "-c", "core.autocrlf=false", "-C", str(dest)]
    subprocess.run([*git, "init", "-q", "-b", "main"], check=True)
    subprocess.run([*git, "fast-import", "--quiet"], input=build_stream(initial_files()), check=True)
    subprocess.run([*git, "reset", "--hard", "-q", "main"], check=True)
    return dest


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("dest", nargs="?", help="directory to create (default: new temp dir)")
    args = ap.parse_args(argv)
    print(generate(args.dest))
    return 0


if __name__ == "__main__":
    sys.exit(main())
