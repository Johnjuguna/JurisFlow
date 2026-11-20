"""Daily deadline checks. Reuses send() and partner_recipients() from hearing_jobs."""

import json
from html import escape

import frappe
from frappe.utils import add_days, get_url_to_form, getdate, now_datetime, today

from jurisflow.engines.deadline_calc import reminders_due
from jurisflow.jobs.hearing_jobs import partner_recipients, send

FIELDS = ["name", "matter", "title", "due_date", "assigned_to", "rule_snapshot", "reminders_sent"]


def _line(d):
    matter = frappe.db.get_value("Legal Matter", d.matter, "title") or d.matter
    link = get_url_to_form("Computed Deadline", d.name)
    return (f"<p><b>{escape(d.title or '')}</b> on matter <a href='{link}'>{escape(matter)}</a>"
            f"<br>Due: {frappe.format(d.due_date, 'Date')}</p>"
            "<p><i>Computed from a verified rule. The advocate remains responsible for the date.</i></p>")


def send_reminders():
    t = getdate(today())
    for d in frappe.get_all("Computed Deadline", filters={"status": "Open"}, fields=FIELDS):
        snap = json.loads(d.rule_snapshot or "{}")
        sent = json.loads(d.reminders_sent or "[]")
        rows = reminders_due(getdate(d.due_date), snap.get("reminders", []), t, sent)
        if not rows:
            continue
        who = set()
        for r in rows:
            if r["recipient"] in ("Responsible advocate", "Both") and d.assigned_to:
                who.add(d.assigned_to)
            if r["recipient"] in ("Partners", "Both"):
                who.update(partner_recipients())
        days_left = (getdate(d.due_date) - t).days
        if send(list(who), f"Deadline in {days_left} day(s): {d.title}", _line(d)):
            frappe.db.set_value("Computed Deadline", d.name, "reminders_sent",
                                json.dumps(sorted(set(sent) | {int(r["days_before"]) for r in rows})),
                                update_modified=False)


def escalate():
    window = int(frappe.get_cached_doc("JF Deadline Settings").escalate_within_days or 0)
    for d in frappe.get_all("Computed Deadline", fields=FIELDS, filters={
            "status": "Open", "assigned_to": ["is", "not set"], "escalated_on": ["is", "not set"],
            "due_date": ["<=", add_days(today(), window)]}):
        if send(partner_recipients(), f"ACTION: deadline with no advocate assigned: {d.title}", _line(d)):
            frappe.db.set_value("Computed Deadline", d.name, "escalated_on", now_datetime(), update_modified=False)

    for d in frappe.get_all("Computed Deadline", fields=FIELDS,
                            filters={"status": "Open", "due_date": ["<", today()]}):
        doc = frappe.get_doc("Computed Deadline", d.name)
        doc.status = "Missed"
        doc.save(ignore_permissions=True)
        send(partner_recipients(), f"DEADLINE MISSED: {d.title}", _line(d))


def run_deadline_checks():
    send_reminders()  # before escalate(), so a due-today reminder is not skipped
    escalate()
    frappe.db.commit()
