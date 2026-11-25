import frappe
from frappe import _
from frappe.utils import flt, today

ITEM_CODE = "Legal Services"
UOM = "Hour"


def _ensure_uom():
	if not frappe.db.exists("UOM", UOM):
		frappe.get_doc({"doctype": "UOM", "uom_name": UOM, "must_be_whole_number": 0}).insert(
			ignore_permissions=True
		)
	elif frappe.db.get_value("UOM", UOM, "must_be_whole_number"):
		frappe.db.set_value("UOM", UOM, "must_be_whole_number", 0)


def _ensure_item():
	if frappe.db.exists("Item", ITEM_CODE):
		return
	_ensure_uom()
	frappe.get_doc(
		{
			"doctype": "Item",
			"item_code": ITEM_CODE,
			"item_name": ITEM_CODE,
			"item_group": "Services",
			"is_stock_item": 0,
			"stock_uom": UOM,
		}
	).insert(ignore_permissions=True)


def refresh_unbilled(matter):
	from jurisflow.services.matter_service import refresh_matter_summary

	refresh_matter_summary(matter, touch=False)


@frappe.whitelist()
def create_invoice_for_matter(matter):
	frappe.has_permission("Sales Invoice", "create", throw=True)
	m = frappe.get_doc("Legal Matter", matter)
	m.check_permission("read")
	rows = frappe.db.sql(
		"""select name, entry_date, advocate, narration, hours, rate
        from `tabLegal Time Entry`
        where matter=%s and billable=1 and billed=0 and docstatus=1
        order by entry_date, creation for update""",
		matter,
		as_dict=True,
	)
	if not rows:
		frappe.throw(_("No unbilled time entries for this matter."))
	_ensure_item()
	inv = frappe.new_doc("Sales Invoice")
	inv.customer = m.customer
	inv.company = m.company or frappe.defaults.get_user_default("Company")
	inv.due_date = today()
	for r in rows:
		inv.append(
			"items",
			{
				"item_code": ITEM_CODE,
				"qty": r.hours,
				"rate": r.rate,
				"description": f"{r.entry_date} | {r.advocate} | {r.narration}",
			},
		)
	inv.remarks = f"Legal matter {m.name}: {m.title}"
	inv.insert()
	for r in rows:
		frappe.db.set_value(
			"Legal Time Entry", r.name, {"billed": 1, "invoice": inv.name}, update_modified=False
		)
	refresh_unbilled(matter)
	return inv.name


def release_entries(doc, method=None):
	"""Sales Invoice cancelled or deleted: make its time entries billable again."""
	matters = set()
	for r in frappe.get_all("Legal Time Entry", filters={"invoice": doc.name}, fields=["name", "matter"]):
		frappe.db.set_value("Legal Time Entry", r.name, {"billed": 0, "invoice": None}, update_modified=False)
		matters.add(r.matter)
	for matter in matters:
		refresh_unbilled(matter)
