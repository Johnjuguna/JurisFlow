import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, today


class ComputedDeadline(Document):
	def validate(self):
		before = self.get_doc_before_save()
		if before and before.status == "Superseded":
			frappe.throw(_("A superseded deadline cannot be changed"))
		if self.calculated_due_date and getdate(self.due_date) != getdate(self.calculated_due_date):
			if not (self.override_reason or "").strip():
				frappe.throw(_("Give a reason for changing the due date from the calculated date"))
		if self.status == "Waived" and not (self.override_reason or "").strip():
			frappe.throw(_("Give a reason for waiving a deadline"))
		if self.status == "Met" and not self.met_on:
			self.met_on = today()

	def on_trash(self):
		frappe.throw(_("Deadlines cannot be deleted. Mark them Met, Waived or Superseded."))


@frappe.whitelist()
def mark_met(name):
	doc = frappe.get_doc("Computed Deadline", name)
	doc.check_permission("write")
	doc.status = "Met"
	doc.save()
	return doc.status
