from datetime import timedelta

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_time, get_url_to_form, getdate, now_datetime, today

from jurisflow.engines.hearing_clock import seconds_of
from jurisflow.services.matter_service import refresh_matter_summary


class CourtHearing(Document):
	def validate(self):
		self.apply_matter_defaults()
		self.validate_status_and_dates()
		self.track_confirmation()
		self.check_clash()

	def on_update(self):
		self.create_or_move_next_hearing()
		refresh_matter_summary(self.matter)

	def after_delete(self):
		refresh_matter_summary(self.matter)

	def apply_matter_defaults(self):
		if not self.matter:
			return
		m = frappe.db.get_value("Legal Matter", self.matter, ["court", "responsible_advocate"], as_dict=True)
		if not m:
			return
		if not self.court and m.court:
			self.court = m.court
		if not self.attending_advocate and m.responsible_advocate:
			self.attending_advocate = m.responsible_advocate

	def validate_status_and_dates(self):
		if self.status in ("Attended", "Adjourned") and getdate(self.hearing_date) > getdate(today()):
			frappe.throw(_("A hearing in the future cannot be marked {0}.").format(self.status))

		if self.status == "Adjourned":
			if not self.adjournment_reason:
				frappe.throw(_("Please give the adjournment reason."))
			if not self.next_date:
				frappe.throw(
					_("An adjourned hearing must have a next date, otherwise the matter will be forgotten.")
				)
			if getdate(self.next_date) <= getdate(self.hearing_date):
				frappe.throw(_("Next date must be after the hearing date."))

		if self.status == "Attended" and not self.outcome:
			frappe.msgprint(
				_("Remember to record the outcome of this hearing."), indicator="orange", alert=True
			)

	def track_confirmation(self):
		if self.attendance_confirmed and not self.confirmed_on:
			self.confirmed_on = now_datetime()
		elif not self.attendance_confirmed:
			self.confirmed_on = None

	def check_clash(self):
		"""Warn (not block) when the attending advocate is double-booked."""
		if self.status != "Scheduled" or not (self.attending_advocate and self.hearing_date):
			return

		others = frappe.get_all(
			"Court Hearing",
			filters={
				"attending_advocate": self.attending_advocate,
				"hearing_date": self.hearing_date,
				"status": "Scheduled",
				"name": ["!=", self.name or ""],
			},
			fields=["name", "court", "hearing_time"],
		)
		mine = seconds_of(self.hearing_time)
		for o in others:
			theirs = seconds_of(o.hearing_time)
			link = get_url_to_form("Court Hearing", o.name)
			if mine is not None and theirs is not None and mine == theirs:
				frappe.msgprint(
					_("Clash: {0} already has hearing <a href='{1}'>{2}</a> at the same time.").format(
						self.attending_advocate, link, o.name
					),
					title=_("Double-booked"),
					indicator="red",
				)
			elif o.court != self.court:
				frappe.msgprint(
					_(
						"{0} also has a hearing the same day in a different court (<a href='{1}'>{2}</a>)."
					).format(self.attending_advocate, link, o.name),
					indicator="orange",
					alert=True,
				)

	def create_or_move_next_hearing(self):
		if self.status != "Adjourned" or not self.next_date:
			return

		if self.next_hearing and frappe.db.exists("Court Hearing", self.next_hearing):
			nxt = frappe.get_doc("Court Hearing", self.next_hearing)
			if nxt.status == "Scheduled" and getdate(nxt.hearing_date) != getdate(self.next_date):
				nxt.hearing_date = self.next_date
				nxt.save(ignore_permissions=True)
			return

		nxt = frappe.get_doc(
			{
				"doctype": "Court Hearing",
				"matter": self.matter,
				"court": self.court,
				"hearing_date": self.next_date,
				"purpose": self.purpose or "Mention",
				"status": "Scheduled",
				"attending_advocate": self.attending_advocate,
			}
		).insert(ignore_permissions=True)

		self.db_set("next_hearing", nxt.name, update_modified=False)
		frappe.msgprint(
			_("Next hearing {0} created for {1}.").format(nxt.name, frappe.format(self.next_date, "Date")),
			indicator="green",
			alert=True,
		)
