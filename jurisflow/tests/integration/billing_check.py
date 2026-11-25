import frappe
from frappe.utils import today

from jurisflow.services import billing_service as bs
from jurisflow.tests.integration.helpers import make_cleared_customer


def say(label, ok, extra=""):
	print(("PASS  " if ok else "FAIL  ") + label, extra)


def run():
	frappe.set_user("Administrator")
	if not frappe.db.exists("Court", "Milimani Law Courts"):
		frappe.get_doc(
			{
				"doctype": "Court",
				"court_name": "Milimani Law Courts",
				"court_level": "High Court",
				"station": "Nairobi",
			}
		).insert()
	customer, check = make_cleared_customer()
	m = frappe.get_doc(
		{
			"doctype": "Legal Matter",
			"title": "TEST Billing Matter",
			"customer": customer,
			"conflict_check": check,
			"court": "Milimani Law Courts",
			"case_no": "HCCC E002 of 2026",
			"responsible_advocate": "Administrator",
			"status": "Open",
		}
	).insert()
	for hrs, rate in [(2, 5000), (1.5, 6000)]:
		frappe.get_doc(
			{
				"doctype": "Legal Time Entry",
				"matter": m.name,
				"advocate": "Administrator",
				"entry_date": today(),
				"hours": hrs,
				"rate": rate,
				"narration": "Test work",
			}
		).insert().submit()
	inv = bs.create_invoice_for_matter(m.name)
	say("invoice created", bool(inv), inv)
	say("invoice net total = 19000", frappe.db.get_value("Sales Invoice", inv, "net_total") == 19000)
	say(
		"entries marked billed",
		frappe.db.count("Legal Time Entry", {"matter": m.name, "billed": 1, "invoice": inv}) == 2,
	)
	say("matter unbilled = 0", frappe.db.get_value("Legal Matter", m.name, "unbilled_amount") == 0)
	try:
		bs.create_invoice_for_matter(m.name)
		say("second invoice refused", False)
	except frappe.ValidationError:
		say("second invoice refused", True)
	bs.release_entries(frappe.get_doc("Sales Invoice", inv))
	say(
		"release makes entries billable again",
		frappe.db.get_value("Legal Matter", m.name, "unbilled_amount") == 19000,
	)
	frappe.delete_doc("Sales Invoice", inv, force=1)
	print("Test matter left in place:", m.name)


def run_cancel():
	frappe.set_user("Administrator")
	customer, check = make_cleared_customer()
	m = frappe.get_doc(
		{
			"doctype": "Legal Matter",
			"title": "TEST Cancel Matter",
			"customer": customer,
			"conflict_check": check,
			"court": "Milimani Law Courts",
			"case_no": "HCCC E003 of 2026",
			"responsible_advocate": "Administrator",
			"status": "Open",
		}
	).insert()
	frappe.get_doc(
		{
			"doctype": "Legal Time Entry",
			"matter": m.name,
			"advocate": "Administrator",
			"entry_date": today(),
			"hours": 2,
			"rate": 5000,
			"narration": "Cancel test",
		}
	).insert().submit()
	inv = frappe.get_doc("Sales Invoice", bs.create_invoice_for_matter(m.name))
	inv.submit()
	say("invoice submitted", inv.docstatus == 1, inv.name)
	inv.cancel()
	say("cancel allowed", frappe.db.get_value("Sales Invoice", inv.name, "docstatus") == 2)
	say("entries released", frappe.db.get_value("Legal Matter", m.name, "unbilled_amount") == 10000)
