"""Court was free text; it is now a Link. Create a Court record for every value already used."""

import frappe


def execute():
	names = set()
	for dt in ("Legal Matter", "Court Hearing"):
		names |= set(frappe.get_all(dt, filters={"court": ["is", "set"]}, pluck="court"))

	for n in names:
		if not frappe.db.exists("Court", n):
			frappe.get_doc({"doctype": "Court", "court_name": n, "court_level": "Other"}).insert(
				ignore_permissions=True
			)
