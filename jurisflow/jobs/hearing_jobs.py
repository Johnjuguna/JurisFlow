"""Scheduled jobs: daily court brief and unconfirmed-hearing escalation.
Set the site time zone to Africa/Nairobi so the cron times run when you expect."""

from datetime import timedelta
from html import escape

import frappe
from frappe.utils import add_days, get_datetime, get_url_to_form, getdate, now_datetime, strip_html_tags, today

from jurisflow.jurisflow.doctype.court_hearing.court_hearing import seconds_of

DEFAULT_HEARING_SECONDS = 9 * 3600  # hearings with no time are treated as 9:00 for reminders


def send(recipients, subject, message):
    """Send only to real email addresses (the Administrator user has none)."""
    recipients = [r for r in recipients if r and "@" in r]
    if recipients:
        frappe.sendmail(recipients=recipients, subject=subject, message=message)
        return True
    return False


def next_court_day():
    d = getdate(add_days(today(), 1))
    while d.weekday() >= 5:  # skip Saturday and Sunday
        d = d + timedelta(days=1)
    return d


def partner_recipients():
    """Users with the 'Law Firm Partner' role, falling back to System Managers."""
    for role in ("Law Firm Partner", "System Manager"):
        if not frappe.db.exists("Role", role):
            continue
        users = frappe.get_all("Has Role", filters={"role": role, "parenttype": "User"}, pluck="parent")
        users = [
            u
            for u in set(users)
            if u not in ("Administrator", "Guest") and frappe.db.get_value("User", u, "enabled")
        ]
        if users:
            return users
    return []


def hearing_datetime(h):
    secs = seconds_of(h.hearing_time)
    if secs is None:
        secs = DEFAULT_HEARING_SECONDS
    return get_datetime(h.hearing_date) + timedelta(seconds=secs)


def last_outcome(h):
    prev = frappe.get_all(
        "Court Hearing",
        filters={
            "matter": h.matter,
            "hearing_date": ["<", h.hearing_date],
            "status": ["in", ["Attended", "Adjourned"]],
        },
        fields=["outcome", "adjournment_reason"],
        order_by="hearing_date desc",
        limit=1,
    )
    if not prev:
        return "First listed hearing in the system"
    text = strip_html_tags(prev[0].outcome or "").strip()
    reason = prev[0].adjournment_reason
    parts = [p for p in (text[:200], f"Adjourned: {reason}" if reason else "") if p]
    return " | ".join(parts) or "No outcome recorded"


def hearing_rows(hearings):
    rows = []
    for h in hearings:
        matter_title = frappe.db.get_value("Legal Matter", h.matter, "title") or h.matter
        time_txt = str(h.hearing_time)[:5] if h.hearing_time else "time not set"
        rows.append(
            "<tr>"
            f"<td>{escape(time_txt)}</td>"
            f"<td>{escape(str(h.court or ''))}</td>"
            f"<td>{escape(str(h.case_no or ''))}</td>"
            f"<td><a href='{get_url_to_form('Court Hearing', h.name)}'>{escape(matter_title)}</a></td>"
            f"<td>{escape(str(h.purpose or ''))}</td>"
            f"<td>{'Confirmed' if h.attendance_confirmed else '<b>NOT CONFIRMED</b>'}</td>"
            f"<td>{escape(last_outcome(h))}</td>"
            "</tr>"
        )
    return "".join(rows)


TABLE_HEAD = (
    "<table border='1' cellpadding='6' style='border-collapse:collapse'>"
    "<tr><th>Time</th><th>Court</th><th>Case No.</th><th>Matter</th><th>Purpose</th>"
    "<th>Attendance</th><th>Last outcome</th></tr>"
)

HEARING_FIELDS = [
    "name", "matter", "court", "case_no", "hearing_date", "hearing_time",
    "purpose", "attending_advocate", "attendance_confirmed",
]


def send_daily_court_brief():
    day = next_court_day()
    hearings = frappe.get_all(
        "Court Hearing",
        filters={"hearing_date": day, "status": "Scheduled"},
        fields=HEARING_FIELDS,
        order_by="hearing_time asc",
    )
    if not hearings:
        return 0

    by_advocate, unassigned = {}, []
    for h in hearings:
        if h.attending_advocate:
            by_advocate.setdefault(h.attending_advocate, []).append(h)
        else:
            unassigned.append(h)

    day_txt = frappe.format(day, "Date")
    sent = 0
    for advocate, rows in by_advocate.items():
        if send(
            [advocate],
            f"Court brief for {day_txt}: {len(rows)} hearing(s)",
            f"<p>Your hearings for {day_txt}:</p>{TABLE_HEAD}{hearing_rows(rows)}</table>",
        ):
            sent += 1

    if unassigned:
        send(
            partner_recipients(),
            f"ACTION: {len(unassigned)} hearing(s) on {day_txt} have no attending advocate",
            f"<p>Assign an advocate:</p>{TABLE_HEAD}{hearing_rows(unassigned)}</table>",
        )
    return sent


def escalate_unconfirmed_hearings():
    """Hourly. <=48h and unconfirmed: remind the advocate. <=24h: tell the partners."""
    now = now_datetime()
    hearings = frappe.get_all(
        "Court Hearing",
        filters={
            "status": "Scheduled",
            "attendance_confirmed": 0,
            "hearing_date": ["between", [today(), add_days(today(), 2)]],
        },
        fields=HEARING_FIELDS + ["reminded_on", "escalated_on"],
    )

    for h in hearings:
        hours_left = (hearing_datetime(h) - now).total_seconds() / 3600
        if hours_left < 0:
            continue

        if hours_left <= 48 and not h.reminded_on and h.attending_advocate:
            send(
                [h.attending_advocate],
                f"Please confirm attendance: {h.court} on {frappe.format(h.hearing_date, 'Date')}",
                f"<p>You have not confirmed attendance.</p>{TABLE_HEAD}{hearing_rows([h])}</table>",
            )
            frappe.db.set_value("Court Hearing", h.name, "reminded_on", now, update_modified=False)

        if hours_left <= 24 and not h.escalated_on:
            if send(
                partner_recipients(),
                f"ESCALATION: hearing within 24h not confirmed ({h.attending_advocate or 'no advocate'})",
                f"<p>Unconfirmed hearing:</p>{TABLE_HEAD}{hearing_rows([h])}</table>",
            ):
                frappe.db.set_value("Court Hearing", h.name, "escalated_on", now, update_modified=False)

    frappe.db.commit()
