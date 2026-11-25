"""Turns trigger events into computed deadlines using verified rules and the court calendar."""

import json
from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import getdate

from jurisflow.engines.deadline_calc import DEFAULT_MAX_STEPS, compute_with_trace

SETTINGS = "JF Deadline Settings"
TRIGGER_DOCTYPE = "Deadline Trigger Event"
RULE_FIELDS = [
	"name",
	"deadline_title",
	"practice_area",
	"court_level",
	"period_value",
	"period_unit",
	"direction",
	"day_mode",
	"count_start",
	"skip_vacations",
	"roll_rule",
	"is_limitation",
	"statute_reference",
	"verified_by",
	"verified_on",
]


def calendar_dates():
	"""Return (holidays, vacations, holiday_list_name); dates as sets."""
	s = frappe.get_cached_doc(SETTINGS)
	holidays = set()
	if s.holiday_list:
		holidays = {
			getdate(d)
			for d in frappe.get_all("Holiday", filters={"parent": s.holiday_list}, pluck="holiday_date")
		}
	vacations = set()
	for v in s.vacations or []:
		d, end = getdate(v.from_date), getdate(v.to_date)
		while d <= end:
			vacations.add(d)
			d += timedelta(days=1)
	return holidays, vacations, s.holiday_list


def _max_steps():
	return int(frappe.get_cached_doc(SETTINGS).get("max_count_steps") or DEFAULT_MAX_STEPS)


def _coverage_warning(list_name, trigger, due):
	"""Warn when the holiday list does not span the counted period (holidays would be missed)."""
	if not list_name:
		return None
	start, end = frappe.db.get_value("Holiday List", list_name, ["from_date", "to_date"]) or (None, None)
	if not start or not end or trigger < getdate(start) or due > getdate(end):
		return _(
			"Holiday List {0} does not cover {1} to {2}. Public holidays in the uncovered "
			"period were NOT excluded. Check the date."
		).format(list_name, trigger, due)
	return None


def match_rules(matter, trigger_type):
	"""Return {'rules': [...], 'skipped_no_court': n, 'skipped_no_practice_area': n}."""
	m = frappe.db.get_value("Legal Matter", matter, ["practice_area", "court"], as_dict=True)
	practice_area = m.practice_area if m else None
	level = frappe.db.get_value("Court", m.court, "court_level") if m and m.court else None
	result = {"rules": [], "skipped_no_court": 0, "skipped_no_practice_area": 0}
	for r in frappe.get_all(
		"Deadline Rule",
		fields=RULE_FIELDS,
		filters={"active": 1, "trigger_type": trigger_type, "verified_by": ["is", "set"]},
	):
		if r.practice_area and r.practice_area != practice_area:
			if not practice_area:
				result["skipped_no_practice_area"] += 1
			continue
		if r.court_level and r.court_level != level:
			if not level:
				result["skipped_no_court"] += 1
			continue
		r["reminders"] = frappe.get_all(
			"Deadline Reminder Offset",
			filters={"parent": r.name, "parenttype": "Deadline Rule"},
			fields=["days_before", "recipient"],
		)
		result["rules"].append(r)
	return result


def active_rules(matter, trigger_type):
	return match_rules(matter, trigger_type)["rules"]


def generate_report(event):
	"""Create deadlines for a trigger event. Returns {'created': [names], 'warnings': [str]}.
	No UI calls here: the caller decides how to show warnings."""
	if not event.event_date:
		frappe.throw(_("Trigger event date is required"))

	# Serialise concurrent generation for the same event so duplicates cannot slip past the exists check.
	frappe.db.get_value(TRIGGER_DOCTYPE, event.name, "name", for_update=True)

	report = {"created": [], "warnings": []}
	trigger = getdate(event.event_date)
	matched = match_rules(event.matter, event.trigger_type)

	if matched["skipped_no_court"]:
		report["warnings"].append(
			_("Matter has no court: {0} rule(s) that need a court level were skipped.").format(
				matched["skipped_no_court"]
			)
		)
	if matched["skipped_no_practice_area"]:
		report["warnings"].append(
			_("Matter has no practice area: {0} rule(s) that need one were skipped.").format(
				matched["skipped_no_practice_area"]
			)
		)
	if not matched["rules"]:
		report["warnings"].append(
			_(
				"No verified rule matched this trigger. NO deadline was created. "
				"Check limitation and procedural dates manually."
			)
		)
		return report

	advocate = frappe.db.get_value("Legal Matter", event.matter, "responsible_advocate")
	holidays, vacations, list_name = calendar_dates()
	max_steps = _max_steps()

	for r in matched["rules"]:
		existing = frappe.db.get_value(
			"Computed Deadline",
			{"trigger_event": event.name, "rule": r.name, "status": ["!=", "Superseded"]},
			["name", "status"],
			as_dict=True,
		)
		if existing:
			if existing.status in ("Met", "Waived"):
				report["warnings"].append(
					_(
						"Deadline {0} is already {1}, so it was NOT recomputed for the new trigger "
						"details. Check it manually."
					).format(existing.name, existing.status)
				)
			continue

		notes = []
		if r.day_mode == "Court days" and not list_name:
			notes.append(
				_(
					"Rule '{0}' counts court days but no Court Holiday List is set in {1}. "
					"Holidays were NOT excluded. Check the date."
				).format(r.name, SETTINGS)
			)

		trace = compute_with_trace(
			trigger,
			int(r.period_value),
			r.period_unit,
			r.day_mode,
			r.count_start,
			holidays=holidays,
			vacations=vacations,
			skip_vacations=bool(r.skip_vacations),
			roll=r.roll_rule,
			direction=r.direction,
			max_steps=max_steps,
		)
		due = trace["due"]

		if r.day_mode == "Court days":
			coverage = _coverage_warning(list_name, trigger, due)
			if coverage:
				notes.append(coverage)
		if trace["rolled"]:
			notes.append(_("Calculated {0}, moved to {1} ({2}).").format(trace["unrolled"], due, r.roll_rule))

		snapshot = {k: v for k, v in r.items() if k != "reminders"}
		snapshot["reminders"] = [dict(x) for x in r.reminders]
		snapshot["holiday_list"] = list_name or "NONE"
		snapshot["trigger_date"] = trigger
		snapshot["generated_by"] = frappe.session.user

		doc = frappe.get_doc(
			{
				"doctype": "Computed Deadline",
				"matter": event.matter,
				"title": r.deadline_title,
				"rule": r.name,
				"trigger_event": event.name,
				"calculated_due_date": due,
				"due_date": due,
				"rolled_from": trace["unrolled"] if trace["rolled"] else None,
				"calendar_warnings": "\n".join(notes) or None,
				"status": "Open",
				"assigned_to": advocate,
				"is_limitation": r.is_limitation,
				"rule_snapshot": json.dumps(snapshot, default=str),
				"reminders_sent": "[]",
			}
		).insert(ignore_permissions=True)
		report["created"].append(doc.name)
		report["warnings"].extend(notes)
	return report


def generate_for_event(event):
	"""Backward-compatible wrapper: returns created names and shows warnings in the UI."""
	report = generate_report(event)
	for w in report["warnings"]:
		frappe.msgprint(w, indicator="orange")
	return report["created"]


def supersede_for_event(event_name):
	for name in frappe.get_all(
		"Computed Deadline",
		pluck="name",
		filters={"trigger_event": event_name, "status": ["in", ["Open", "Missed"]]},
	):
		doc = frappe.get_doc("Computed Deadline", name)
		doc.superseded_from_status = doc.status
		doc.status = "Superseded"
		doc.save(ignore_permissions=True)


def regenerate_for_event(event):
	supersede_for_event(event.name)
	return generate_for_event(event)
