import json
import pathlib
import unittest

from jurisflow.deadline_hooks import merge_doc_events, merge_scheduler

PKG = pathlib.Path(__file__).resolve().parents[2]
DOCTYPES = list((PKG / "jf_deadlines" / "doctype").glob("*/*.json"))


class TestHooksMerge(unittest.TestCase):
    def test_merge_keeps_existing_jobs(self):
        out = merge_scheduler({"daily": ["a.b"], "cron": {"0 17 * * *": ["x.y"]}})
        self.assertEqual(out["daily"], ["a.b"])
        self.assertEqual(out["cron"]["0 17 * * *"], ["x.y"])

    def test_merge_is_idempotent(self):
        once = merge_scheduler({})
        self.assertEqual(merge_scheduler(once), once)

    def test_doc_events_keep_existing(self):
        out = merge_doc_events({"Legal Matter": {"validate": "p.q"}})
        self.assertEqual(out["Legal Matter"], {"validate": "p.q"})
        self.assertIn("Computed Deadline", out)


class TestDoctypeFiles(unittest.TestCase):
    def test_found_all_doctypes(self):
        self.assertEqual(len(DOCTYPES), 7)

    def test_no_doctype_allows_delete(self):
        for p in DOCTYPES:
            for perm in json.loads(p.read_text())["permissions"]:
                self.assertEqual(perm.get("delete", 0), 0, p.name)

    def test_select_defaults_are_valid_options(self):
        for p in DOCTYPES:
            for f in json.loads(p.read_text())["fields"]:
                if f["fieldtype"] == "Select" and f.get("default"):
                    self.assertIn(f["default"], f["options"].split("\n"), f"{p.name}.{f['fieldname']}")

    def test_every_table_field_points_to_a_child_doctype(self):
        names = {json.loads(p.read_text())["name"]: json.loads(p.read_text()) for p in DOCTYPES}
        for d in names.values():
            for f in d["fields"]:
                if f["fieldtype"] == "Table":
                    self.assertEqual(names[f["options"]]["istable"], 1)

    def test_every_doctype_has_controller(self):
        for p in DOCTYPES:
            self.assertTrue(p.with_suffix(".py").exists(), p.name)
