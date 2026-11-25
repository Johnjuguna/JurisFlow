import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class LegalTimeEntry(Document):
	def validate(self):
		if flt(self.hours) <= 0:
			frappe.throw(_("Hours must be greater than zero."))
		if not self.rate:
			area = frappe.db.get_value("Legal Matter", self.matter, "practice_area")
			self.rate = flt(frappe.db.get_value("Practice Area", area, "default_hourly_rate"))
		self.amount = flt(self.hours) * flt(self.rate)

	def on_submit(self):
		self.refresh_matter()

	def on_cancel(self):
		if self.billed:
			frappe.throw(_("Cannot cancel a billed time entry."))
		self.refresh_matter()

	def refresh_matter(self):
		from jurisflow.services.billing_service import refresh_unbilled

		refresh_unbilled(self.matter)
