"""Pure deadline arithmetic. Stdlib only, no database: fully unit-testable.

Counting conventions are parameters, not assumptions. Which convention a statute needs is
decided by the advocate who verifies the Deadline Rule, never by this code.
"""

from calendar import monthrange
from datetime import date, timedelta

_MAX_STEPS = 20000


def add_months(d, months):
    """Calendar-month arithmetic; clamps to the last day of a shorter month (31 Jan + 1m = 28 Feb)."""
    y, m = divmod(d.month - 1 + months, 12)
    year, month = d.year + y, m + 1
    return date(year, month, min(d.day, monthrange(year, month)[1]))


def is_working_day(d, holidays=frozenset(), vacations=frozenset(), skip_vacations=False):
    if d.weekday() >= 5 or d in holidays:
        return False
    return not (skip_vacations and d in vacations)


def _counts(d, day_mode, holidays, vacations, skip_vacations):
    if day_mode == "Court days":
        return is_working_day(d, holidays, vacations, skip_vacations)
    return not (skip_vacations and d in vacations)


def _count_days(trigger, value, sign, day_mode, count_start, holidays, vacations, skip_vacations):
    if value == 0:
        return trigger
    cursor = trigger if count_start == "Same day" else trigger + timedelta(days=sign)
    remaining = value
    for _ in range(_MAX_STEPS):
        if _counts(cursor, day_mode, holidays, vacations, skip_vacations):
            remaining -= 1
            if remaining == 0:
                return cursor
        cursor += timedelta(days=sign)
    raise ValueError("Period is too long to compute")


def _roll(d, roll, holidays, vacations, skip_vacations):
    if roll not in ("Next working day", "Previous working day"):
        return d
    step = timedelta(days=1 if roll == "Next working day" else -1)
    for _ in range(_MAX_STEPS):
        if is_working_day(d, holidays, vacations, skip_vacations):
            return d
        d += step
    raise ValueError("No working day found")


def compute_due_date(trigger, value, unit="Days", day_mode="Calendar days",
                     count_start="Day after trigger", holidays=frozenset(), vacations=frozenset(),
                     skip_vacations=False, roll="None", direction="After"):
    """Return the due date. Months/Years are calendar anniversaries (count_start does not apply)."""
    if value < 0:
        raise ValueError("Period cannot be negative")
    sign = 1 if direction == "After" else -1
    if unit in ("Months", "Years"):
        due = add_months(trigger, sign * value * (12 if unit == "Years" else 1))
    elif unit in ("Days", "Weeks"):
        if unit == "Weeks":
            if day_mode == "Court days":
                raise ValueError("Court days can only be used with unit Days")
            value *= 7
        due = _count_days(trigger, value, sign, day_mode, count_start, holidays, vacations, skip_vacations)
    else:
        raise ValueError(f"Unknown unit: {unit}")
    return _roll(due, roll, holidays, vacations, skip_vacations)


def reminders_due(due, reminders, today, sent):
    """Reminder rows to send now. `reminders` = [{'days_before': int, 'recipient': str}], `sent` = [int].
    Overdue deadlines get none (they are handled as 'missed')."""
    days_left = (due - today).days
    if days_left < 0:
        return []
    return [r for r in reminders
            if days_left <= int(r["days_before"]) and int(r["days_before"]) not in sent]
