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
        if self.has_value_changed("event_date") or self.has_value_changed("trigger_type"):
            from jurisflow.services import deadline_service
            deadline_service.regenerate_for_event(self)

    def on_trash(self):
        frappe.throw(_("Trigger events cannot be deleted. Correct the date and the deadlines will be recomputed."))
