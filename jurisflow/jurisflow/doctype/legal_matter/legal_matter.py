import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, today


class LegalMatter(Document):
    def validate(self):
        if self.status == "Closed" and not self.closed_on:
            self.closed_on = today()
        if self.status != "Closed":
            self.closed_on = None
        self.set_unbilled_amount()

    def set_unbilled_amount(self):
        if self.is_new():
            self.unbilled_amount = 0
            return
        total = frappe.db.sql(
            """SELECT IFNULL(SUM(amount), 0) FROM `tabLegal Time Entry`
               WHERE matter=%s AND billable=1 AND billed=0 AND docstatus=1""",
            self.name,
        )[0][0]
        self.unbilled_amount = flt(total)



@frappe.whitelist()
def create_invoice(matter):
    frappe.has_permission("Sales Invoice", "create", throw=True)
    m = frappe.get_doc("Legal Matter", matter)
    entries = frappe.get_all(
        "Legal Time Entry",
        filters={"matter": matter, "billable": 1, "billed": 0, "docstatus": 1},
        fields=["name", "entry_date", "advocate", "narration", "hours", "rate"],
        order_by="entry_date asc",
    )
    if not entries:
        frappe.throw(_("No unbilled time entries for this matter."))
    item_code = "Legal Services"
    if not frappe.db.exists("Item", item_code):
        frappe.get_doc({
            "doctype": "Item", "item_code": item_code, "item_name": item_code,
            "item_group": "Services", "is_stock_item": 0, "stock_uom": "Nos",
        }).insert(ignore_permissions=True)

    inv = frappe.new_doc("Sales Invoice")
    inv.customer = m.customer
    inv.company = m.company or frappe.defaults.get_user_default("Company")
    for e in entries:
        inv.append("items", {
            "item_code": item_code,
            "description": f"{e.entry_date} | {e.advocate} | {e.narration}",
            "qty": e.hours,
            "rate": e.rate,
        })
    inv.remarks = f"Legal matter {m.name}: {m.title}"
    inv.insert()

    for e in entries:
        frappe.db.set_value("Legal Time Entry", e.name, {"billed": 1, "invoice": inv.name})
    return inv.name
