import frappe
from jurisflow.tests.integration.helpers import make_cleared_customer


def say(label, ok, extra=""):
    print(("PASS  " if ok else "FAIL  ") + label, extra)


def _matter():
    if not frappe.db.exists("Court", "Milimani Law Courts"):
        frappe.get_doc({"doctype": "Court", "court_name": "Milimani Law Courts",
                        "court_level": "High Court", "station": "Nairobi"}).insert()
    cust, chk = make_cleared_customer()
    return frappe.get_doc({"doctype": "Legal Matter", "title": "TEST Fee Note Matter",
        "customer": cust, "conflict_check": chk, "court": "Milimani Law Courts",
        "case_no": "HCCC E010 of 2026", "responsible_advocate": "Administrator",
        "status": "Open"}).insert()


def run_totals():
    frappe.set_user("Administrator")
    m = _matter()
    fn = frappe.get_doc({"doctype": "Fee Note", "matter": m.name, "lines": [
        {"line_type": "Fee", "description": "Advice", "qty": 1, "rate": 10000, "vat_applicable": 1},
        {"line_type": "Disbursement", "description": "Filing fee", "qty": 1, "rate": 2000, "vat_applicable": 0},
    ]}).insert()
    say("fees = 10000", fn.total_fees == 10000)
    say("disbursements = 2000", fn.total_disbursements == 2000)
    say("VAT on fees only = 1600", fn.vat_amount == 1600)
    say("grand total = 13600", fn.grand_total == 13600, fn.name)
