"""Daily deadline checks. Reuses send() and partner_recipients() from hearing_jobs.

Each deadline is processed on its own: a failure is logged and the run continues, so one bad
record can never stop reminders for everyone else. Work is committed per deadline."""

import json
from html import escape

import frappe
from frappe.utils import add_days, get_url_to_form, getdate, now_datetime, today

from jurisflow.engines.deadline_calc import reminders_due
from jurisflow.jobs.hearing_jobs import partner_recipients, send

FIELDS = ["name", "matter", "title", "due_date", "assigned_to", "rule_snapshot", "reminders_sent"]
LOG_TITLE = "JurisFlow deadline job"


def _line(d):
	matter = frappe.db.get_value("Legal Matter", d.matter, "title") or d.matter
	link = get_url_to_form("Computed Deadline", d.name)
	return (
		f"<p><b>{escape(d.title or '')}</b> on matter <a href='{link}'>{escape(matter)}</a>"
		f"<br>Due: {frappe.format(d.due_date, 'Date')}</p>"
		"<p><i>Computed from a verified rule. The advocate remains responsible for the date.</i></p>"
	)


def _safe(step, d):
	"""Run step(d) and commit. On failure: roll back that item only, log it, carry on."""
	try:
		step(d)
		frappe.db.commit()
	except Exception:
		frappe.db.rollback()
		frappe.log_error(title=f"{LOG_TITLE}: {d.name}", message=frappe.get_traceback())
		frappe.db.commit()


def _remind(d, t):
	snap = json.loads(d.rule_snapshot or "{}")
	sent = json.loads(d.reminders_sent or "[]")
	rows = reminders_due(getdate(d.due_date), snap.get("reminders", []), t, sent)
	if not rows:
		return
	who = set()
	for r in rows:
		if r["recipient"] in ("Responsible advocate", "Both") and d.assigned_to:
			who.add(d.assigned_to)
		if r["recipient"] in ("Partners", "Both"):
			who.update(partner_recipients())
	if not who:
		raise ValueError(f"No recipient for the reminder on {d.name}: no assigned advocate and no partners")
	days_left = (getdate(d.due_date) - t).days
	if not send(list(who), f"Deadline in {days_left} day(s): {d.title}", _line(d)):
		raise RuntimeError(f"Reminder for {d.name} was not sent")
	frappe.db.set_value(
		"Computed Deadline",
		d.name,
		"reminders_sent",
		json.dumps(sorted(set(sent) | {int(r["days_before"]) for r in rows})),
		update_modified=False,
	)


def _escalate_unassigned(d):
	if not send(partner_recipients(), f"ACTION: deadline with no advocate assigned: {d.title}", _line(d)):
		raise RuntimeError(f"Escalation for {d.name} was not sent")
	frappe.db.set_value("Computed Deadline", d.name, "escalated_on", now_datetime(), update_modified=False)


def _mark_missed(d):
	doc = frappe.get_doc("Computed Deadline", d.name)
	doc.status = "Missed"
	doc.save(ignore_permissions=True)
	frappe.db.commit()  # the Missed status is the truth: keep it even if the email below fails
	if not send(partner_recipients(), f"DEADLINE MISSED: {d.title}", _line(d)):
		raise RuntimeError(f"{d.name} is marked Missed but the partner alert was NOT sent")


def send_reminders():
	t = getdate(today())
	for d in frappe.get_all("Computed Deadline", filters={"status": "Open"}, fields=FIELDS):
		_safe(lambda x: _remind(x, t), d)


def escalate():
	window = int(frappe.get_cached_doc("JF Deadline Settings").escalate_within_days or 0)
	for d in frappe.get_all(
		"Computed Deadline",
		fields=FIELDS,
		filters={
			"status": "Open",
			"assigned_to": ["is", "not set"],
			"escalated_on": ["is", "not set"],
			"due_date": ["<=", add_days(today(), window)],
		},
	):
		_safe(_escalate_unassigned, d)

	for d in frappe.get_all(
		"Computed Deadline", fields=FIELDS, filters={"status": "Open", "due_date": ["<", today()]}
	):
		_safe(_mark_missed, d)


def run_deadline_checks():
	send_reminders()  # before escalate(), so a due-today reminder is not skipped
	escalate()
