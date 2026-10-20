"""Render deterministic before/after dependency diagrams from the committed sample report.

    python demo/make_sample_report.py && python demo/render_dependency_graphs.py

Only Python's standard library is used; no network or external renderer is needed.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPORT = ROOT / "sample-report"
POSITIONS = {
    "src/billing": (120, 170),
    "src/identity": (350, 65),
    "src/reporting": (350, 170),
    "src/notifications": (350, 275),
    "src/shared": (580, 170),
}
LABELS = {
    "src/billing": "Billing",
    "src/identity": "Identity",
    "src/reporting": "Reporting",
    "src/notifications": "Notifications",
    "src/shared": "Shared",
}


def _svg(title, edges, path):
    nodes = sorted({node for edge in edges for node in edge[:2]})
    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="760" height="360" viewBox="0 0 760 360">',
        '<defs><marker id="arrow" markerWidth="9" markerHeight="7" refX="8" refY="3.5" orient="auto">',
        '<polygon points="0 0, 9 3.5, 0 7" fill="context-stroke"/></marker></defs>',
        '<rect width="100%" height="100%" fill="#fbfcfe"/>',
        '<text x="28" y="34" font-family="Arial,sans-serif" font-size="20" font-weight="bold" fill="#172b4d">'
        + title + '</text>',
    ]
    for src, dst, label, kind in edges:
        x1, y1 = POSITIONS[src]
        x2, y2 = POSITIONS[dst]
        color = "#c0392b" if kind == "cycle" else ("#2874a6" if kind == "event" else "#596780")
        dash = ' stroke-dasharray="7 6"' if kind == "event" else ""
        lines.append(f'<line x1="{x1 + 64}" y1="{y1}" x2="{x2 - 64}" y2="{y2}" '
                     f'stroke="{color}" stroke-width="2.4"{dash} marker-end="url(#arrow)"/>')
        midx, midy = (x1 + x2) // 2, (y1 + y2) // 2 - 8
        lines.append(f'<text x="{midx}" y="{midy}" text-anchor="middle" font-family="Arial,sans-serif" '
                     f'font-size="11" fill="{color}">{label}</text>')
    for node in nodes:
        x, y = POSITIONS[node]
        fill = "#fdecea" if node == "src/billing" else "#eaf2f8"
        lines.append(f'<rect x="{x - 64}" y="{y - 22}" width="128" height="44" rx="10" fill="{fill}" '
                     'stroke="#344563" stroke-width="1.5"/>')
        lines.append(f'<text x="{x}" y="{y + 5}" text-anchor="middle" font-family="Arial,sans-serif" '
                     f'font-size="14" fill="#172b4d">{LABELS[node]}</text>')
    lines += [
        '<text x="28" y="335" font-family="Arial,sans-serif" font-size="11" fill="#596780">'
        'Solid = synchronous/import dependency · dashed = asynchronous event</text>',
        '</svg>',
        '',
    ]
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def main():
    report = json.loads((REPORT / "findings.json").read_text(encoding="utf-8"))
    before = []
    for edge in report["dependencies"]["edges"]:
        kind = "cycle" if edge["mutual"] else "sync"
        before.append((edge["src"], edge["dst"], f"{edge['weight']} import(s)", kind))
    after = [
        ("src/billing", "src/identity", "authorize", "sync"),
        ("src/billing", "src/notifications", "notify", "sync"),
        ("src/billing", "src/reporting", "invoice-completed event", "event"),
    ]
    _svg("Before: measured sample imports", before, REPORT / "dependencies-before.svg")
    _svg("After: proposed async Reporting boundary", after, REPORT / "dependencies-after.svg")
    print(f"Wrote dependency diagrams to {REPORT}")


if __name__ == "__main__":
    main()
