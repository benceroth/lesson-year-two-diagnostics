import unittest

from fixture import demo_result


class PlantedPatterns(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.res = demo_result()

    def test_cross_team_change_coupling_found(self):
        pair = self.res["coupling"]["file_pairs"][0]
        self.assertEqual({pair["a"], pair["b"]}, {"src/billing/invoice.py", "src/reporting/export.py"})
        self.assertGreaterEqual(pair["support"], 25)
        self.assertTrue(pair["cross_module"] and pair["cross_team"])

    def test_weaker_coupling_also_found(self):
        pairs = {frozenset((p["a"], p["b"])) for p in self.res["coupling"]["file_pairs"] if p["cross_module"]}
        self.assertIn(frozenset(("src/billing/invoice.py", "src/identity/authz.py")), pairs)

    def test_mass_reformat_commit_does_not_create_coupling(self):
        self.assertEqual(self.res["coupling"]["skipped_large_commits"], 2)  # initial import + reformat
        cross = [p for p in self.res["coupling"]["file_pairs"] if p["cross_module"]]
        self.assertEqual(len(cross), 2)

    def test_hotspot_is_invoice(self):
        files = self.res["hotspots"]["files"]
        self.assertEqual(files[0]["path"], "src/billing/invoice.py")
        self.assertGreater(files[0]["score"], 10 * files[1]["score"])

    def test_ownership_bottleneck_is_billing_only(self):
        flagged = [m for m in self.res["ownership"]["modules"] if m["bottleneck"]]
        self.assertEqual([m["module"] for m in flagged], ["src/billing"])
        self.assertEqual(flagged[0]["owner"], "billing")
        self.assertGreaterEqual(flagged[0]["teams_touching"], 4)
        self.assertLess(flagged[0]["owner_share"], 0.5)

    def test_billing_has_highest_inbound_share(self):
        self.assertEqual(self.res["ownership"]["teams"][0]["team"], "billing")

    def test_ownership_is_team_level_only(self):
        for t in self.res["ownership"]["teams"]:
            self.assertEqual(set(t), {"team", "commits_authored", "authors", "small_team",
                                      "cross_team_commit_share", "commits_touching_its_files", "inbound_share"})

    def test_dependency_cycle_billing_reporting(self):
        self.assertIn(["src/billing", "src/reporting"], self.res["dependencies"]["cycles"])
        self.assertIn("src_billing", self.res["dependency_mermaid"])
        self.assertIn('"src/billing" -> "src/reporting"', self.res["dependency_dot"])


if __name__ == "__main__":
    unittest.main()
