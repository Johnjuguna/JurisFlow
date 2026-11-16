"""Pure date/time rules for court hearings. No database access, so it is unit-testable."""

from datetime import timedelta

from frappe.utils import get_datetime, get_time

DEFAULT_HEARING_SECONDS = 9 * 3600  # a hearing with no time is treated as 09:00


def seconds_of(t):
    """Normalise a Time value (str / time / timedelta / None) to seconds since midnight."""
    if t in (None, ""):
        return None
    if isinstance(t, timedelta):
        return int(t.total_seconds())
    t = get_time(t)
    return t.hour * 3600 + t.minute * 60 + t.second


def hearing_moment(hearing_date, hearing_time):
    secs = seconds_of(hearing_time)
    if secs is None:
        secs = DEFAULT_HEARING_SECONDS
    return get_datetime(hearing_date) + timedelta(seconds=secs)


def next_court_day(after, holidays=frozenset()):
    """First day after `after` that is not a weekend and not in `holidays` (a set of dates)."""
    d = after + timedelta(days=1)
    while d.weekday() >= 5 or d in holidays:
        d += timedelta(days=1)
    return d
