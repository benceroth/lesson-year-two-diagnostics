import subprocess
import tempfile
import unittest
from pathlib import Path

import fixture  # noqa: F401
from y2diag.analyzers import dependency_map
from y2diag.config import Config
from y2diag.teams import TeamResolver

FILES = {
    "app/web/main.py": "from app.core import service\nfrom . import helpers\nimport os\n",
    "app/web/helpers.py": "x = 1\n",
    "app/core/service.py": "from app.web import helpers\n",
    "ui/a/index.js": "import { b } from '../b/util';\nconst c = require('./local');\nimport react from 'react';\n",
    "ui/a/local.ts": "export const l = 1;\n",
    "ui/b/util.js": "export const b = 1;\n",
}


class DependencyMapTests(unittest.TestCase):
    def test_python_and_js_edges(self):
        with tempfile.TemporaryDirectory() as d:
            for rel, text in FILES.items():
                p = Path(d) / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(text, encoding="utf-8")
            subprocess.run(["git", "-C", d, "init", "-q"], check=True)
            subprocess.run(["git", "-C", d, "add", "-A"], check=True)
            cfg = Config()
            deps = dependency_map.analyze(d, TeamResolver(cfg), cfg)
        edges = {(e["src"], e["dst"]) for e in deps["edges"]}
        self.assertEqual(edges, {("app/web", "app/core"), ("app/core", "app/web"), ("ui/a", "ui/b")})
        self.assertEqual(deps["cycles"], [["app/core", "app/web"]])
        self.assertIn("graph LR", dependency_map.to_mermaid(deps))


if __name__ == "__main__":
    unittest.main()
