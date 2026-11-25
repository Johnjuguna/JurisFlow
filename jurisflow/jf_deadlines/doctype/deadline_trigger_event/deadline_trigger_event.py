import frappe
from frappe import _
from frappe.model.document import Document


class DeadlineTriggerEvent(Document):
	def after_insert(self):
		from jurisflow.services import deadline_service

		deadline_service.generate_for_event(self)

	def on_update(self):
		if self.flags.in_insert:
			return
		if any(self.has_value_changed(f) for f in ("event_date", "trigger_type", "matter")):
			from jurisflow.services import deadline_service

			deadline_service.regenerate_for_event(self)

	def on_trash(self):
		frappe.throw(
			_("Trigger events cannot be deleted. Correct the date and the deadlines will be recomputed.")
		)
