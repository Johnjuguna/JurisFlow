"""Read access to the conflict settings. Everything the firm can configure is read here,
so if the storage ever moves, this is the only module that changes."""

import frappe
from frappe.utils import cint

from jurisflow.engines.conflict_matcher import DEFAULT_THRESHOLD

SETTINGS = "JF Compliance Settings"


def _settings():
	return frappe.get_cached_doc(SETTINGS, SETTINGS)


def _column(table, fieldname):
	return [row.get(fieldname) for row in (_settings().get(table) or []) if row.get(fieldname)]


def gate_enabled():
	val = _settings().get("enforce_conflict_gate")
	return True if val is None else bool(cint(val))


def match_threshold():
	pct = cint(_settings().get("name_match_threshold"))
	return (min(pct, 100) / 100) if pct > 0 else DEFAULT_THRESHOLD


def clearance_validity_days():
	return max(cint(_settings().get("clearance_validity_days")), 0)


def partner_roles():
	return set(_column("partner_roles", "role"))


def exempt_party_roles():
	return set(_column("exempt_party_roles", "party_role"))


def informational_pairs():
	"""(searched as, found in) pairs that are recorded but do not stop a matter."""
	return {
		(row.get("searched_as"), row.get("found_in"))
		for row in (_settings().get("informational_rules") or [])
		if row.get("searched_as") and row.get("found_in")
	}
