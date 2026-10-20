from .build import build_sections

TABLE_KEYS = ("table", "table2", "table3")


def _cell(v):
    return str(v).replace("|", "\\|")


def _table(t):
    lines = ["| " + " | ".join(t["headers"]) + " |", "|" + "---|" * len(t["headers"])]
    for row in t["rows"]:
        lines.append("| " + " | ".join(_cell(c) for c in row) + " |")
    if not t["rows"]:
        lines.append("| " + " | ".join(["_none_"] + [""] * (len(t["headers"]) - 1)) + " |")
    return "\n".join(lines)


def render_markdown(res):
    out = [f"# Year-two architecture diagnostics: {res['meta']['name']}", ""]
    for s in build_sections(res):
        out += [f"## {s['title']}", ""]
        for p in s.get("paragraphs", []):
            out += [p, ""]
        for b in s.get("bullets", []):
            out.append(f"- {b}")
        if s.get("bullets"):
            out.append("")
        for key in TABLE_KEYS:
            t = s.get(key)
            if t:
                if t.get("caption"):
                    out += [f"**{t['caption']}**", ""]
                out += [_table(t), ""]
        if s.get("code"):
            lang, body = s["code"]
            out += [f"```{lang}", body.rstrip("\n"), "```", ""]
    return "\n".join(out).rstrip("\n") + "\n"
