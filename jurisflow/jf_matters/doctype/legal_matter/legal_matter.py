import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import today


class LegalMatter(Document):
	def validate(self):
		if self.status == "Closed":
			self.validate_can_close()
			if not self.closed_on:
				self.closed_on = today()
		elif self.status in ("Open", "On Hold"):
			self.closed_on = None

	def validate_can_close(self):
		if self.is_new():
			return
		upcoming = frappe.get_all(
			"Court Hearing",
			filters={"matter": self.name, "status": "Scheduled", "hearing_date": [">=", today()]},
			pluck="name",
		)
		if upcoming:
			frappe.throw(
				_(
					"Cannot close this matter: it still has scheduled hearings ({0}). Cancel or complete them first."
				).format(", ".join(upcoming))
			)

		open_tasks = frappe.db.count(
			"Matter Task", {"matter": self.name, "status": ["in", ["Open", "In Progress"]]}
		)
		if open_tasks:
			frappe.msgprint(
				_("This matter still has {0} open task(s).").format(open_tasks),
				indicator="orange",
				alert=True,
			)
