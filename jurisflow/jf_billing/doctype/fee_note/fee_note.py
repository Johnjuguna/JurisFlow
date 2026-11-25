import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class FeeNote(Document):
	def validate(self):
		if not self.lines:
			frappe.throw(_("Add at least one line."))
		fees = disb = vat_base = 0
		for r in self.lines:
			r.amount = flt(r.qty) * flt(r.rate)
			if r.line_type == "Fee":
				fees += r.amount
			else:
				disb += r.amount
			if r.vat_applicable:
				vat_base += r.amount
		self.total_fees = fees
		self.total_disbursements = disb
		self.vat_amount = round(vat_base * flt(self.vat_rate) / 100, 2)
		self.grand_total = fees + disb + self.vat_amount

	def before_cancel(self):
		inv = self.sales_invoice
		if inv and frappe.db.get_value("Sales Invoice", inv, "docstatus") != 2:
			frappe.throw(_("Cancel Sales Invoice {0} first.").format(inv))
