import frappe
from jurisflow.jurisflow.doctype.legal_matter.legal_matter import create_invoice


def run():
    if not frappe.db.exists("Customer", "Test Client Ltd"):
        frappe.get_doc({"doctype": "Customer", "customer_name": "Test Client Ltd",
                        "customer_type": "Company"}).insert()
    m = frappe.get_doc({
        "doctype": "Legal Matter", "title": "Test v Test",
        "customer": "Test Client Ltd", "practice_area": "Litigation",
        "responsible_advocate": "Administrator", "court": "High Court Nairobi",
        "case_no": "HCCC 123 of 2026",
    }).insert()
    t = frappe.get_doc({
        "doctype": "Legal Time Entry", "matter": m.name,
        "advocate": "Administrator", "hours": 2.5, "rate": 15000,
        "narration": "Drafted plaint",
    }).insert()
    t.submit()
    print("Matter:", m.name, "| Time entry:", t.name, "| Amount:", t.amount)
    print("Invoice:", create_invoice(m.name))
    frappe.db.commit()
