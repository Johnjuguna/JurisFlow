import frappe
from frappe import _
from frappe.utils import today

from jurisflow.services.billing_service import UOM, _ensure_uom

FEE_ITEM = "Legal Fees"
DISB_ITEM = "Disbursements"
NO_VAT = "JF Disbursement No VAT"


def _item(code):
	if frappe.db.exists("Item", code):
		return
	_ensure_uom()
	frappe.get_doc(
		{
			"doctype": "Item",
			"item_code": code,
			"item_name": code,
			"item_group": "Services",
			"is_stock_item": 0,
			"stock_uom": UOM,
		}
	).insert(ignore_permissions=True)


def _no_vat_template(company, vat_account):
	name = frappe.db.get_value("Item Tax Template", {"title": NO_VAT, "company": company})
	if name:
		return name
	doc = frappe.get_doc(
		{
			"doctype": "Item Tax Template",
			"title": NO_VAT,
			"company": company,
			"taxes": [{"tax_type": vat_account, "tax_rate": 0}],
		}
	)
	doc.insert(ignore_permissions=True)
	return doc.name


def _assign_to_item(code, template):
	item = frappe.get_doc("Item", code)
	field = next(f.fieldname for f in item.meta.get_table_fields() if f.options == "Item Tax")
	if any(r.item_tax_template == template for r in item.get(field)):
		return
	item.append(field, {"item_tax_template": template})
	item.save(ignore_permissions=True)


def create_invoice_on_submit(doc, method=None):
	if doc.sales_invoice:
		return
	company = (
		doc.company
		or frappe.db.get_value("Legal Matter", doc.matter, "company")
		or frappe.defaults.get_user_default("Company")
	)
	tmpl = doc.tax_template or frappe.db.get_value(
		"Sales Taxes and Charges Template", {"company": company}, "name"
	)
	if not tmpl:
		frappe.throw(_("No sales tax template found for {0}.").format(company))
	tdoc = frappe.get_doc("Sales Taxes and Charges Template", tmpl)
	no_vat = _no_vat_template(company, tdoc.taxes[0].account_head)
	_item(FEE_ITEM)
	_item(DISB_ITEM)
	_assign_to_item(DISB_ITEM, no_vat)
	inv = frappe.new_doc("Sales Invoice")
	inv.customer, inv.company, inv.due_date = doc.customer, company, today()
	inv.taxes_and_charges = tmpl
	for t in tdoc.taxes:
		inv.append(
			"taxes",
			{
				"charge_type": t.charge_type,
				"account_head": t.account_head,
				"description": t.description,
				"rate": t.rate,
				"cost_center": t.cost_center,
			},
		)
	for r in doc.lines:
		row = {
			"item_code": FEE_ITEM if r.vat_applicable else DISB_ITEM,
			"qty": r.qty,
			"rate": r.rate,
			"description": r.description,
		}
		if not r.vat_applicable:
			row["item_tax_template"] = no_vat
		inv.append("items", row)
	inv.matter = doc.matter
	inv.remarks = f"Fee Note {doc.name} - matter {doc.matter}"
	inv.insert()
	doc.db_set("sales_invoice", inv.name)


def release_draft_invoice(doc, method=None):
	inv = doc.sales_invoice
	if inv and frappe.db.get_value("Sales Invoice", inv, "docstatus") == 0:
		doc.db_set("sales_invoice", None)
		frappe.delete_doc("Sales Invoice", inv, force=1)
