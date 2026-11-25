import unittest

from jurisflow.engines.conflict_matcher import find_matches, name_similarity, normalize_id, normalize_name

CANDS = [
    {"source": "Customer", "record": "C1", "name": "Acme Limited", "id_number": "P051234567A"},
    {"source": "Matter Party", "record": "M1", "name": "Wanjiru Mwangi", "id_number": "12345678"},
    {"source": "Matter Party", "record": "M2", "name": "Peter Otieno", "id_number": None},
]


class TestConflictMatcher(unittest.TestCase):
    def test_normalize_name(self):
        self.assertEqual(normalize_name("  Mr. John  O'Brien "), "john o brien")
        self.assertEqual(normalize_name("Smith & Sons Ltd"), normalize_name("SMITH AND SONS LIMITED"))
        self.assertEqual(normalize_name("José Muñoz"), "jose munoz")
        self.assertEqual(normalize_name(None), "")
        self.assertEqual(normalize_name("Ltd"), "")

    def test_normalize_id(self):
        self.assertEqual(normalize_id("p05-123 4567a"), "P051234567A")
        self.assertEqual(normalize_id(None), "")

    def test_similarity(self):
        self.assertEqual(name_similarity("Acme Limited", "ACME LTD"), 1.0)
        self.assertEqual(name_similarity("John Kamau Njuguna", "Njuguna Kamau John"), 1.0)
        self.assertEqual(name_similarity("John Kamau", "John Kamau Njuguna"), 0.9)
        self.assertGreaterEqual(name_similarity("Jon Kamau", "John Kamau"), 0.85)
        self.assertLess(name_similarity("John Kamau", "James Kamau"), 0.85)
        self.assertEqual(name_similarity("", "x"), 0.0)

    def test_exact_name_hit(self):
        hits = find_matches("ACME LTD", None, CANDS)
        self.assertEqual([h["record"] for h in hits], ["C1"])
        self.assertEqual(hits[0]["reason"], "Exact name match")

    def test_id_match_beats_different_name(self):
        hits = find_matches("Someone Else", "123-456-78", CANDS)
        self.assertEqual([h["record"] for h in hits], ["M1"])
        self.assertEqual(hits[0]["reason"], "ID / PIN match")

    def test_short_ids_are_ignored(self):
        self.assertEqual(find_matches("Zed", "1234", [{"source": "x", "record": "1", "name": "Qq", "id_number": "1234"}]), [])

    def test_no_hit(self):
        self.assertEqual(find_matches("Totally Unrelated", None, CANDS), [])

    def test_best_match_first(self):
        cands = [{"source": "x", "record": "1", "name": "Jon Kamau"}, {"source": "x", "record": "2", "name": "John Kamau"}]
        self.assertEqual([h["record"] for h in find_matches("John Kamau", None, cands)], ["2", "1"])
