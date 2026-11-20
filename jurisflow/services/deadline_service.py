"""Turns trigger events into computed deadlines using verified rules and the court calendar."""

import json
from datetime import timedelta

import frappe
from frappe.utils import getdate

from jurisflow.engines.deadline_calc import compute_due_date

SETTINGS = "JF Deadline Settings"
RULE_FIELDS = ["name", "deadline_title", "practice_area", "court_level", "period_value", "period_unit",
               "direction", "day_mode", "count_start", "skip_vacations", "roll_rule", "is_limitation",
               "statute_reference", "verified_by", "verified_on"]


def calendar_dates():
    """Return (holidays, vacations, holiday_list_name); dates as sets."""
    s = frappe.get_cached_doc(SETTINGS)
    holidays = set()
    if s.holiday_list:
        holidays = {getdate(d) for d in frappe.get_all(
            "Holiday", filters={"parent": s.holiday_list}, pluck="holiday_date")}
    vacations = set()
    for v in s.vacations or []:
        d, end = getdate(v.from_date), getdate(v.to_date)
        while d <= end:
            vacations.add(d)
            d += timedelta(days=1)
    return holidays, vacations, s.holiday_list


def active_rules(matter, trigger_type):
    m = frappe.db.get_value("Legal Matter", matter, ["practice_area", "court"], as_dict=True)
    level = frappe.db.get_value("Court", m.court, "court_level") if m and m.court else None
    out = []
    for r in frappe.get_all("Deadline Rule", fields=RULE_FIELDS, filters={
            "active": 1, "trigger_type": trigger_type, "verified_by": ["is", "set"]}):
        if r.practice_area and r.practice_area != (m.practice_area if m else None):
            continue
        if r.court_level and r.court_level != level:
            continue
        r["reminders"] = frappe.get_all(
            "Deadline Reminder Offset", filters={"parent": r.name, "parenttype": "Deadline Rule"},
            fields=["days_before", "recipient"])
        out.append(r)
    return out


def generate_for_event(event):
    advocate = frappe.db.get_value("Legal Matter", event.matter, "responsible_advocate")
    holidays, vacations, list_name = calendar_dates()
    created = []
    for r in active_rules(event.matter, event.trigger_type):
        if frappe.db.exists("Computed Deadline", {
                "trigger_event": event.name, "rule": r.name, "status": ["!=", "Superseded"]}):
            continue
        if r.day_mode == "Court days" and not list_name:
            frappe.msgprint(f"Rule '{r.name}' counts court days but no Court Holiday List is set in "
                            f"{SETTINGS}. Holidays were NOT excluded. Check the date.", indicator="orange")
        due = compute_due_date(
            getdate(event.event_date), int(r.period_value), r.period_unit, r.day_mode, r.count_start,
            holidays=holidays, vacations=vacations, skip_vacations=bool(r.skip_vacations),
            roll=r.roll_rule, direction=r.direction)
        snapshot = {k: (str(v) if v is not None else None) for k, v in r.items() if k != "reminders"}
        snapshot["reminders"] = [dict(x) for x in r.reminders]
        snapshot["holiday_list"] = list_name or "NONE"
        snapshot["trigger_date"] = str(getdate(event.event_date))
        doc = frappe.get_doc({
            "doctype": "Computed Deadline", "matter": event.matter, "title": r.deadline_title,
            "rule": r.name, "trigger_event": event.name, "calculated_due_date": due, "due_date": due,
            "status": "Open", "assigned_to": advocate, "is_limitation": r.is_limitation,
            "rule_snapshot": json.dumps(snapshot), "reminders_sent": "[]",
        }).insert(ignore_permissions=True)
        created.append(doc.name)
    return created


def supersede_for_event(event_name):
    for name in frappe.get_all("Computed Deadline", pluck="name", filters={
            "trigger_event": event_name, "status": ["in", ["Open", "Missed"]]}):
        doc = frappe.get_doc("Computed Deadline", name)
        doc.status = "Superseded"
        doc.save(ignore_permissions=True)


def regenerate_for_event(event):
    supersede_for_event(event.name)
    return generate_for_event(event)
