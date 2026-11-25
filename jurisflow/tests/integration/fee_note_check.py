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


def run_flow():
    from jurisflow.services import fee_note_service as svc
    from frappe.utils import today
    frappe.set_user("Administrator")
    m = _matter()
    frappe.get_doc({"doctype": "Legal Time Entry", "matter": m.name, "advocate": "Administrator",
                    "entry_date": today(), "hours": 2, "rate": 5000, "narration": "FN flow"}).insert().submit()
    fn = frappe.get_doc({"doctype": "Fee Note", "matter": m.name, "lines": [
        {"line_type": "Disbursement", "description": "Filing fee", "qty": 1, "rate": 1000, "vat_applicable": 0}]}).insert()
    say("time entries loaded", svc.load_time_entries(fn.name) == 1)
    fn.reload()
    say("total fees = 10000", fn.total_fees == 10000, fn.total_fees)
    fn.submit()
    say("entry marked billed", frappe.db.count("Legal Time Entry", {"matter": m.name, "billed": 1}) == 1)
    fn.cancel()
    say("cancel releases entry", frappe.db.count("Legal Time Entry", {"matter": m.name, "billed": 0}) == 1)
