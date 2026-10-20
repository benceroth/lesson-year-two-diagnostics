import unittest
from pathlib import Path

import fixture  # noqa: F401  (sets sys.path)
from y2diag.config import Config, load_config, parse_simple_yaml
from y2diag.teams import TeamResolver, parse_codeowners


class ConfigTests(unittest.TestCase):
    def test_parse_yaml_subset(self):
        data = parse_simple_yaml(
            "# c\nteams:\n  billing:\n    - src/billing/  # trailing\n"
            'authors:\n  "a-*@x.test": billing\nsince: 2024-01-01\nmin_support: 7\nignore: ["*.lock", vendor/]\n'
        )
        self.assertEqual(data["teams"], {"billing": ["src/billing/"]})
        self.assertEqual(data["authors"], {"a-*@x.test": "billing"})
        self.assertEqual(data["min_support"], 7)
        self.assertEqual(data["ignore"], ["*.lock", "vendor/"])

    def test_example_config_loads(self):
        cfg = load_config(Path(fixture.ROOT) / "tool" / "config.example.yaml")
        self.assertIn("billing", cfg.teams)
        self.assertEqual(cfg.min_support, 5)

    def test_unknown_key_rejected(self):
        p = Path(fixture.ROOT) / "tests" / "_bad.yaml"
        p.write_text("nope: 1\n", encoding="utf-8")
        try:
            with self.assertRaises(ValueError):
                load_config(p)
        finally:
            p.unlink()


class TeamTests(unittest.TestCase):
    CODEOWNERS = "* @org/platform\n/src/billing/ @org/billing\n*.md @org/docs\n/src/billing/legacy/ @org/legacy\n"

    def test_codeowners_last_match_wins(self):
        r = TeamResolver(Config(), parse_codeowners(self.CODEOWNERS))
        self.assertEqual(r.team_of_path("src/billing/a.py"), "billing")
        self.assertEqual(r.team_of_path("src/billing/legacy/a.py"), "legacy")
        self.assertEqual(r.team_of_path("README.md"), "docs")
        self.assertEqual(r.team_of_path("other/x.py"), "platform")

    def test_config_wins_over_codeowners(self):
        r = TeamResolver(Config(teams={"payments": ["src/billing/"]}), parse_codeowners(self.CODEOWNERS))
        self.assertEqual(r.team_of_path("src/billing/a.py"), "payments")

    def test_author_mapping(self):
        r = TeamResolver(Config(authors={"billing-*@x.test": "billing"}))
        self.assertEqual(r.team_of_author("Billing-1@x.test"), "billing")
        self.assertEqual(r.team_of_author("someone@else"), "unmapped")


if __name__ == "__main__":
    unittest.main()
