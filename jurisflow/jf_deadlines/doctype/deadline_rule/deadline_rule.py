import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import today

# Changing any of these after verification voids it (the advocate must re-check).
LOGIC_FIELDS = (
	"trigger_type",
	"period_value",
	"period_unit",
	"direction",
	"day_mode",
	"count_start",
	"skip_vacations",
	"roll_rule",
	"statute_reference",
)


def verifier_roles():
	s = frappe.get_cached_doc("JF Deadline Settings")
	return {r.role for r in (s.verifier_roles or [])}


class DeadlineRule(Document):
	def validate(self):
		if not self.period_value or int(self.period_value) <= 0:
			frappe.throw(_("Period must be greater than zero"))
		if self.day_mode == "Court days" and self.period_unit != "Days":
			frappe.throw(_("Court days can only be used with unit Days"))
		self.guard_verification()
		if self.active and not self.verified_by:
			frappe.throw(_("A rule must be verified by an advocate before it can be activated"))

	def guard_verification(self):
		if self.flags.verifying:
			return
		if self.is_new():
			if self.verified_by or self.verified_on:
				frappe.throw(_("Verification can only be given with the Verify action"))
			return
		if self.has_value_changed("verified_by") or self.has_value_changed("verified_on"):
			frappe.throw(_("Verification can only be given with the Verify action"))
		if any(self.has_value_changed(f) for f in LOGIC_FIELDS) and self.verified_by:
			self.verified_by = None
			self.verified_on = None
			self.active = 0
			frappe.msgprint(
				_("The rule changed, so it was deactivated and needs to be verified again."), alert=True
			)

	def on_trash(self):
		frappe.throw(_("Deadline rules cannot be deleted. Deactivate the rule instead."))


@frappe.whitelist()
def verify_rule(name):
	allowed = verifier_roles()
	if not allowed:
		frappe.throw(_("No verifier roles are set in JF Deadline Settings"))
	if not (set(frappe.get_roles()) & allowed):
		frappe.throw(_("You are not allowed to verify deadline rules"), frappe.PermissionError)
	doc = frappe.get_doc("Deadline Rule", name)
	doc.flags.verifying = True
	doc.verified_by = frappe.session.user
	doc.verified_on = today()
	doc.save(ignore_permissions=True)
	return doc.verified_by
