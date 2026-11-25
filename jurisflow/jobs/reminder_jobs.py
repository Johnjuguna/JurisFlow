import frappe
from frappe.utils import add_days, today


def send_hearing_reminders():
	for days in (1, 3):
		hearings = frappe.get_all(
			"Court Hearing",
			filters={"hearing_date": add_days(today(), days), "status": "Scheduled"},
			fields=["name", "matter", "hearing_date", "hearing_time", "court", "purpose"],
		)
		for h in hearings:
			advocate = frappe.db.get_value("Legal Matter", h.matter, "responsible_advocate")
			if not advocate:
				continue
			frappe.sendmail(
				recipients=[advocate],
				subject=f"Hearing in {days} day(s): {h.matter}",
				message=f"Matter: {h.matter}<br>Court: {h.court}<br>Date: {h.hearing_date} {h.hearing_time or ''}<br>Purpose: {h.purpose}",
			)
