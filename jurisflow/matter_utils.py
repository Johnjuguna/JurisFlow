"""Keeps the summary fields on Legal Matter correct by recomputing them from the real records."""

import frappe
from frappe.utils import flt, today


def refresh_matter_summary(matter, touch=True):
    if not matter or not frappe.db.exists("Legal Matter", matter):
        return

    next_hearing = frappe.get_all(
        "Court Hearing",
        filters={"matter": matter, "status": "Scheduled", "hearing_date": [">=", today()]},
        pluck="hearing_date",
        order_by="hearing_date asc",
        limit=1,
    )

    limitation = frappe.get_all(
        "Matter Task",
        filters={
            "matter": matter,
            "task_type": "Limitation Date",
            "status": ["not in", ["Done", "Cancelled"]],
            "due_date": ["is", "set"],
        },
        pluck="due_date",
        order_by="due_date asc",
        limit=1,
    )

    unbilled_total = frappe.db.sql(
        """select coalesce(sum(amount), 0) from `tabLegal Time Entry`
        where matter = %s and billable = 1 and billed = 0""",
        matter,
    )[0][0]

    values = {
        "next_hearing_date": next_hearing[0] if next_hearing else None,
        "limitation_date": limitation[0] if limitation else None,
        "unbilled_amount": flt(unbilled_total),
    }
    if touch:
        values["last_activity_on"] = today()

    frappe.db.set_value("Legal Matter", matter, values, update_modified=False)


def refresh_from_doc(doc, method=None):
    """doc_events handler for Matter Task and Legal Time Entry."""
    refresh_matter_summary(doc.get("matter"))


def time_entry_validate(doc, method=None):
    """amount = hours x rate; billed follows the invoice link; client comes from the matter."""
    if doc.matter:
        matter = frappe.db.get_value(
            "Legal Matter", doc.matter, ["customer", "practice_area"], as_dict=True
        )
        if matter:
            if not doc.customer:
                doc.customer = matter.customer
            if not flt(doc.rate) and matter.practice_area:
                doc.rate = frappe.db.get_value("Practice Area", matter.practice_area, "default_hourly_rate") or 0

    doc.amount = flt(doc.hours) * flt(doc.rate)
    doc.billed = 1 if doc.invoice else 0
