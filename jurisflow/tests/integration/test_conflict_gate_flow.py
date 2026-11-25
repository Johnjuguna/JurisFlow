"""Integration tests for the conflict gate: real service, real settings, real database.

Run on a development site only. Every test starts from a known settings baseline and is rolled back.
Names and identifiers are random so they cannot collide with real clients.
"""

import random
import string

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, now_datetime

from jurisflow.patches.seed_conflict_settings import INFORMATIONAL
from jurisflow.services import conflict_service as svc

SETTINGS = "JF Compliance Settings"


def rand_name():
	"""A single random token, so two names are never similar to each other."""
	return "".join(random.choices(string.ascii_lowercase, k=12)).capitalize()


def rand_id():
	return "".join(random.choices(string.ascii_uppercase + string.digits, k=11))


def configure(**values):
	doc = frappe.get_doc(SETTINGS, SETTINGS)
	for key, value in values.items():
		doc.set(key, value)
	doc.save(ignore_permissions=True)
	frappe.clear_document_cache(SETTINGS, SETTINGS)


def party_type():
	"""First valid option of the field, so the tests do not hardcode a label."""
	options = frappe.get_meta("Conflict Check").get_field("party_type").options or ""
	return next(o for o in options.split("\n") if o.strip())


def make_check(party=None, adverse=None, id_number=None, other_names=None, search=True):
	doc = frappe.get_doc(
		{
			"doctype": "Conflict Check",
			"party_name": party or rand_name(),
			"party_type": party_type(),
			"id_number": id_number,
			"adverse_party": adverse,
			"other_names": other_names,
		}
	).insert(ignore_permissions=True)
	if search:
		svc.run_search(doc.name)
	return frappe.get_doc("Conflict Check", doc.name)


def make_matter(check=None, customer=None, opposing=None, parties=()):
	matter = frappe.new_doc("Legal Matter")
	matter.conflict_check = check.name if check else None
	matter.customer = customer
	matter.opposing_party = opposing
	for row in parties:
		matter.append("parties", row)
	return matter


class TestConflictGateFlow(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		configure(
			enforce_conflict_gate=1,
			clearance_validity_days=0,
			partner_roles=[{"role": "System Manager"}],
			exempt_party_roles=[],
			informational_rules=[{"searched_as": a, "found_in": f} for a, f in INFORMATIONAL],
		)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()
		frappe.clear_document_cache(SETTINGS, SETTINGS)

	# --- opening a matter ----------------------------------------------------------------

	def test_matter_without_a_check_is_refused(self):
		with self.assertRaisesRegex(frappe.ValidationError, "required"):
			svc.enforce_gate(make_matter())

	def test_check_that_was_never_run_is_refused(self):
		check = make_check(search=False)
		with self.assertRaisesRegex(frappe.ValidationError, "must be clear"):
			svc.enforce_gate(make_matter(check))

	def test_check_with_unresolved_conflict_is_refused(self):
		found = self._conflict_found()
		with self.assertRaisesRegex(frappe.ValidationError, "must be clear"):
			svc.enforce_gate(make_matter(found, opposing=found.adverse_party))

	def test_clear_check_covering_the_opposing_party_is_accepted(self):
		check = make_check(adverse=rand_name())
		svc.enforce_gate(make_matter(check, opposing=check.adverse_party))

	def test_gate_can_be_switched_off_in_settings(self):
		configure(enforce_conflict_gate=0)
		svc.enforce_gate(make_matter())

	# --- coverage ------------------------------------------------------------------------

	def test_uncovered_opposing_party_is_refused(self):
		check = make_check(adverse=rand_name())
		with self.assertRaisesRegex(frappe.ValidationError, "not covered"):
			svc.enforce_gate(make_matter(check, opposing=rand_name()))

	def test_uncovered_party_row_is_refused(self):
		check = make_check(adverse=rand_name())
		rows = [{"party_name": rand_name(), "role": "Witness"}]
		with self.assertRaisesRegex(frappe.ValidationError, "not covered"):
			svc.enforce_gate(make_matter(check, opposing=check.adverse_party, parties=rows))

	def test_exempt_role_needs_no_coverage(self):
		configure(exempt_party_roles=[{"party_role": "Witness"}])
		check = make_check(adverse=rand_name())
		rows = [{"party_name": rand_name(), "role": "Witness"}]
		svc.enforce_gate(make_matter(check, opposing=check.adverse_party, parties=rows))

	def test_party_covered_by_identifier_is_accepted(self):
		ident = rand_id()
		check = make_check(adverse=rand_name(), id_number=ident)
		rows = [{"party_name": rand_name(), "id_number": ident.lower(), "role": "Witness"}]
		svc.enforce_gate(make_matter(check, opposing=check.adverse_party, parties=rows))

	# --- reuse, expiry, client -----------------------------------------------------------

	def test_check_cannot_be_used_by_a_second_matter(self):
		check = make_check(adverse=rand_name())
		first = make_matter(check, opposing=check.adverse_party)
		first.flags.ignore_mandatory = True  # only the gate is under test, not other required fields
		first.insert(ignore_permissions=True)
		with self.assertRaisesRegex(frappe.ValidationError, "already used"):
			svc.enforce_gate(make_matter(check, opposing=check.adverse_party))

	def test_expired_check_is_refused_when_validity_is_set(self):
		check = make_check(adverse=rand_name())
		frappe.db.set_value("Conflict Check", check.name, "run_on", add_days(now_datetime(), -40))
		configure(clearance_validity_days=30)
		with self.assertRaisesRegex(frappe.ValidationError, "days ago"):
			svc.enforce_gate(make_matter(check, opposing=check.adverse_party))

	def test_old_check_is_accepted_when_validity_is_zero(self):
		check = make_check(adverse=rand_name())
		frappe.db.set_value("Conflict Check", check.name, "run_on", add_days(now_datetime(), -400))
		svc.enforce_gate(make_matter(check, opposing=check.adverse_party))

	def test_check_cleared_for_a_different_client_is_refused(self):
		check_a, check_b = make_check(adverse=rand_name()), make_check(adverse=rand_name())
		svc.create_customer(check_a.name)
		customer_b = svc.create_customer(check_b.name)
		check_a.reload()
		with self.assertRaisesRegex(frappe.ValidationError, "different client"):
			svc.enforce_gate(make_matter(check_a, customer=customer_b, opposing=check_a.adverse_party))

	# --- partner decisions ---------------------------------------------------------------

	def test_user_without_a_partner_role_is_refused(self):
		email = f"{rand_name().lower()}@example.com"
		frappe.get_doc(
			{"doctype": "User", "email": email, "first_name": "NoRole", "send_welcome_email": 0}
		).insert(ignore_permissions=True)
		frappe.set_user(email)
		with self.assertRaises(frappe.PermissionError):
			svc.require_partner()

	def test_no_configured_partner_roles_blocks_everyone(self):
		configure(partner_roles=[])
		with self.assertRaisesRegex(frappe.ValidationError, "No roles are allowed"):
			svc.require_partner()

	def test_decision_needs_a_reason(self):
		found = self._conflict_found()
		with self.assertRaisesRegex(frappe.ValidationError, "reason"):
			svc.decide(found.name, svc.STATUS_CLEARED, "   ")

	def test_decision_only_applies_to_a_check_with_conflicts(self):
		check = make_check()
		with self.assertRaisesRegex(frappe.ValidationError, "conflicts found"):
			svc.decide(check.name, svc.STATUS_CLEARED, "reason")

	def test_partner_clearance_lets_the_matter_through(self):
		found = self._conflict_found()
		svc.decide(found.name, svc.STATUS_CLEARED, "Reviewed; no real conflict.")
		found.reload()
		svc.enforce_gate(make_matter(found, opposing=found.adverse_party))

	def test_declined_check_is_refused(self):
		found = self._conflict_found()
		svc.decide(found.name, svc.STATUS_DECLINED, "Conflict is real.")
		found.reload()
		with self.assertRaisesRegex(frappe.ValidationError, "must be clear"):
			svc.enforce_gate(make_matter(found, opposing=found.adverse_party))

	# --- helpers -------------------------------------------------------------------------

	def _conflict_found(self):
		"""A check whose adverse party is an existing customer, which blocks under the baseline rules."""
		existing = make_check()
		svc.create_customer(existing.name)
		found = make_check(adverse=existing.party_name)
		self.assertEqual(found.status, svc.STATUS_FOUND, "fixture should produce a blocking conflict")
		return found
