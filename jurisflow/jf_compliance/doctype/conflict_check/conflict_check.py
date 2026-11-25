import frappe
from frappe import _
from frappe.model.document import Document

SEARCH_FIELDS = ("party_name", "party_type", "id_number", "adverse_party", "other_names")
LOCKED = ("No Conflict", "Cleared by Partner", "Declined")
# Only conflict_service may change these, so the result cannot be edited by hand or through the API.
PROTECTED = ("status", "hit_count", "run_by", "run_on", "cleared_by", "cleared_on", "clearance_notes", "customer")


class ConflictCheck(Document):
    def validate(self):
        if not self.status:
            self.status = "Not Run"
        self.guard_protected_fields()
        self.guard_search_inputs()

    def guard_protected_fields(self):
        if self.flags.via_service:
            return
        before = self.get_doc_before_save()
        for f in PROTECTED:
            old = before.get(f) if before else ("Not Run" if f == "status" else None)
            if (self.get(f) or None) != (old or None):
                frappe.throw(_("{0} is set by the system and cannot be edited.").format(self.meta.get_label(f)))

    def guard_search_inputs(self):
        before = self.get_doc_before_save()
        if not before:
            return
        if not any((before.get(f) or "") != (self.get(f) or "") for f in SEARCH_FIELDS):
            return
        if before.status in LOCKED:
            frappe.throw(_("This check is already decided. Open a new Conflict Check for different details."))
        # details changed after a search: the old result no longer applies
        self.status = "Not Run"
        self.hit_count = 0
        self.set("hits", [])
