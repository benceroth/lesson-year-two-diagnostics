import html
import re

from .build import build_sections

CSS = """
body{font:15px/1.5 system-ui,sans-serif;max-width:60rem;margin:2rem auto;padding:0 1rem;color:#222}
table{border-collapse:collapse;margin:.5rem 0 1.2rem;width:100%}
th,td{border:1px solid #ccc;padding:.25rem .5rem;text-align:left;font-size:.9rem}
th{background:#f2f2f2}code,pre{background:#f6f6f6}pre{padding:.7rem;overflow:auto}
.bar{background:#c0392b;height:.8rem;display:inline-block}
"""


def _inline(text):
    text = html.escape(str(text))
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    return re.sub(r"`(.+?)`", r"<code>\1</code>", text)


def _table(t):
    out = []
    if t.get("caption"):
        out.append(f"<h3>{html.escape(t['caption'])}</h3>")
    out.append("<table><tr>" + "".join(f"<th>{html.escape(h)}</th>" for h in t["headers"]) + "</tr>")
    for row in t["rows"]:
        out.append("<tr>" + "".join(f"<td>{html.escape(str(c))}</td>" for c in row) + "</tr>")
    out.append("</table>")
    return "\n".join(out)


def render_html(res):
    name = html.escape(res["meta"]["name"])
    out = [
        "<!doctype html>", '<html lang="en"><head><meta charset="utf-8">',
        f"<title>Year-two diagnostics: {name}</title><style>{CSS}</style></head><body>",
        f"<h1>Year-two architecture diagnostics: {name}</h1>",
    ]
    for s in build_sections(res):
        out.append(f"<h2>{html.escape(s['title'])}</h2>")
        out += [f"<p>{_inline(p)}</p>" for p in s.get("paragraphs", [])]
        if s.get("bullets"):
            out.append("<ul>" + "".join(f"<li>{_inline(b)}</li>" for b in s["bullets"]) + "</ul>")
        for key in ("table", "table2", "table3"):
            if s.get(key):
                out.append(_table(s[key]))
        if s.get("bars"):
            peak = max((v for _, v in s["bars"]), default=1) or 1
            out.append("<h3>Hotspot score</h3><table>")
            for label, v in s["bars"]:
                out.append(f"<tr><td>{html.escape(label)}</td><td><span class='bar' style='width:{round(v / peak * 100)}%'></span> {v}</td></tr>")
            out.append("</table>")
        if s.get("code"):
            out.append(f"<pre>{html.escape(s['code'][1])}</pre>")
    out.append("</body></html>")
    return "\n".join(out) + "\n"
