import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint


class JFComplianceSettings(Document):
    def validate(self):
        if not 50 <= cint(self.name_match_threshold) <= 100:
            frappe.throw(_("Name match threshold must be between 50 and 100."))
