import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

from jurisflow.engines.fee_scale_calc import validate_bands


class FeeScale(Document):
	def validate(self):
		if self.effective_to and getdate(self.effective_to) < getdate(self.effective_from):
			frappe.throw(_("Effective To cannot be before Effective From."))
		errors = validate_bands([b.as_dict() for b in self.bands])
		if errors:
			frappe.throw("<br>".join(_(e) for e in errors))
