import json
import unittest
from datetime import date, datetime

import frappe
from frappe.tests import UnitTestCase

from jurisflow.engines.conflict_gate import (
	clearance_expired,
	same_party,
	split_names,
	uncovered_parties,
	usable_ids,
)
from jurisflow.services import conflict_service

THRESHOLD = 0.85


def party(name, id_number=None, role=None):
	return {"name": name, "id_number": id_number, "role": role}


class TestCoverage(UnitTestCase):
	def test_exact_and_reordered_names_are_covered(self):
		gaps = uncovered_parties(
			[party("Kio Advocate"), party("Advocate Kio")], ["Kio Advocate"], set(), THRESHOLD
		)
		self.assertEqual(gaps, [])

	def test_company_suffix_is_ignored(self):
		self.assertEqual(uncovered_parties([party("ACME Limited")], ["Acme Ltd"], set(), THRESHOLD), [])

	def test_unrelated_party_is_a_gap(self):
		gaps = uncovered_parties([party("Someone Else")], ["Kio Advocate"], set(), THRESHOLD)
		self.assertEqual([g["name"] for g in gaps], ["Someone Else"])

	def test_identifier_covers_a_differently_spelled_name(self):
		ids = usable_ids("A-1234567")
		self.assertEqual(uncovered_parties([party("Totally Different", "a1234567")], [], ids, THRESHOLD), [])

	def test_short_identifiers_are_not_used(self):
		self.assertEqual(usable_ids("123", None, ""), set())

	def test_exempt_role_needs_no_coverage(self):
		gaps = uncovered_parties(
			[party("A Witness", role="witness")], [], set(), THRESHOLD, exempt_roles=["Witness"]
		)
		self.assertEqual(gaps, [])

	def test_no_exempt_roles_means_everyone_is_checked(self):
		gaps = uncovered_parties([party("A Witness", role="Witness")], [], set(), THRESHOLD)
		self.assertEqual(len(gaps), 1)

	def test_blank_names_are_ignored(self):
		self.assertEqual(uncovered_parties([party(""), party(None), party("  ")], [], set(), THRESHOLD), [])


class TestSameParty(UnitTestCase):
	def test_same_identifier_wins_over_different_names(self):
		self.assertTrue(
			same_party("Mabati Millers", "P051234567X", "M. Millers Co", "p051234567x", THRESHOLD)
		)

	def test_same_name_without_identifiers(self):
		self.assertTrue(same_party("Mabati Millers", None, "Millers Mabati", None, THRESHOLD))

	def test_different_identifier_does_not_veto_same_name(self):
		self.assertTrue(same_party("Mabati Millers", "P051234567X", "Mabati Millers", "12345678", THRESHOLD))

	def test_different_parties(self):
		self.assertFalse(same_party("Mabati Millers", None, "Kio Advocate", None, THRESHOLD))


class TestExpiry(UnitTestCase):
	decided = date(2026, 11, 1)

	def test_zero_never_expires(self):
		self.assertFalse(clearance_expired(self.decided, date(2030, 1, 1), 0))
		self.assertFalse(clearance_expired(self.decided, date(2030, 1, 1), None))

	def test_boundary_day_is_still_valid(self):
		self.assertFalse(clearance_expired(self.decided, date(2026, 12, 1), 30))

	def test_day_after_boundary_is_expired(self):
		self.assertTrue(clearance_expired(self.decided, date(2026, 12, 2), 30))

	def test_datetime_is_accepted(self):
		self.assertTrue(clearance_expired(datetime(2026, 11, 1, 9, 30), date(2026, 12, 2), 30))

	def test_missing_decision_date_is_expired_when_expiry_is_on(self):
		self.assertTrue(clearance_expired(None, date(2026, 11, 2), 30))


class TestNames(UnitTestCase):
	def test_split_names(self):
		self.assertEqual(split_names("A\n\n  B  \n"), ["A", "B"])
		self.assertEqual(split_names(None), [])


class TestSchemaMatchesCode(unittest.TestCase):
	"""The Select options in the rule doctype must list exactly the labels the service uses."""

	def test_informational_rule_options(self):
		path = frappe.get_app_path(
			"jurisflow",
			"jf_compliance",
			"doctype",
			"conflict_informational_rule",
			"conflict_informational_rule.json",
		)
		with open(path) as f:
			fields = {x["fieldname"]: x["options"].split("\n") for x in json.load(f)["fields"]}
		self.assertEqual(fields["searched_as"], list(conflict_service.KINDS))
		self.assertEqual(fields["found_in"], list(conflict_service.SOURCES))
