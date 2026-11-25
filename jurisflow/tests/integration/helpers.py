import frappe


def make_cleared_check():
	"""A Conflict Check on a unique name, searched and clear. Returns its name."""
	from jurisflow.services.conflict_service import run_search

	doc = frappe.get_doc(
		{
			"doctype": "Conflict Check",
			"party_type": "Company",
			"party_name": f"ZQ{frappe.generate_hash(length=12)}",
		}
	).insert()
	status = run_search(doc.name)
	assert status == "No Conflict", status
	return doc.name


def make_cleared_customer():
	"""A unique Customer plus a clear Conflict Check cleared for that same name. Returns (customer, check)."""
	check = make_cleared_check()
	party = frappe.db.get_value("Conflict Check", check, "party_name")
	cust = frappe.get_doc(
		{"doctype": "Customer", "customer_name": party, "customer_type": "Company"}
	).insert()
	return cust.name, check
