"""Pure rules for the conflict gate. No database access, so they are easy to unit test."""

from datetime import datetime

from jurisflow.engines.conflict_matcher import MIN_ID_LENGTH, name_similarity, normalize_id


def split_names(text):
	"""One name per line; blank lines dropped."""
	return [line.strip() for line in (text or "").splitlines() if line.strip()]


def usable_ids(*values):
	"""Normalised identifiers long enough to identify a person or company."""
	ids = {normalize_id(v) for v in values}
	return {i for i in ids if len(i) >= MIN_ID_LENGTH}


def is_covered(name, id_number, covered_names, covered_ids, threshold):
	"""True if the party was searched, by a matching identifier or a similar enough name."""
	if usable_ids(id_number) & set(covered_ids):
		return True
	return any(name_similarity(name, covered) >= threshold for covered in covered_names)


def uncovered_parties(parties, covered_names, covered_ids, threshold, exempt_roles=()):
	"""parties: dicts with name, id_number, role. Returns those the check did not cover.

	Parties whose role is in exempt_roles need no coverage; blank names are ignored.
	"""
	exempt = {_fold(r) for r in exempt_roles if _fold(r)}
	gaps = []
	for party in parties:
		name = (party.get("name") or "").strip()
		if not name or _fold(party.get("role")) in exempt:
			continue
		if not is_covered(name, party.get("id_number"), covered_names, covered_ids, threshold):
			gaps.append(party)
	return gaps


def same_party(name_a, id_a, name_b, id_b, threshold):
	"""Same identifier, or a similar enough name. Differing identifiers never veto a name match,
	because a customer may hold a KRA PIN while the check holds a national ID."""
	if usable_ids(id_a) & usable_ids(id_b):
		return True
	return name_similarity(name_a, name_b) >= threshold


def clearance_expired(decided_on, on_date, validity_days):
	"""validity_days of 0 (or unset) means a clearance never expires.
	With expiry on, a clearance with no decision date cannot be shown to be fresh, so it is expired."""
	if not validity_days or validity_days <= 0:
		return False
	if not decided_on:
		return True
	return (_as_date(on_date) - _as_date(decided_on)).days > validity_days


def _as_date(value):
	return value.date() if isinstance(value, datetime) else value


def _fold(value):
	return (value or "").strip().casefold()
