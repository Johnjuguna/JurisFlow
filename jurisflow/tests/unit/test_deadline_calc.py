import unittest
from datetime import date

from jurisflow.engines.deadline_calc import add_months, compute_due_date, reminders_due

MON = date(2026, 11, 16)
FRI = date(2026, 11, 20)


class TestDeadlineCalc(unittest.TestCase):
    def test_calendar_days_count_from_day_after_trigger(self):
        self.assertEqual(compute_due_date(MON, 14), date(2026, 11, 30))

    def test_same_day_counts_trigger_as_day_one(self):
        self.assertEqual(compute_due_date(MON, 14, count_start="Same day"), date(2026, 11, 29))

    def test_roll_to_next_working_day(self):
        self.assertEqual(compute_due_date(MON, 14, count_start="Same day", roll="Next working day"), date(2026, 11, 30))

    def test_roll_to_previous_working_day(self):
        self.assertEqual(compute_due_date(MON, 14, count_start="Same day", roll="Previous working day"), date(2026, 11, 27))

    def test_court_days_skip_weekends(self):
        self.assertEqual(compute_due_date(FRI, 3, day_mode="Court days"), date(2026, 11, 25))

    def test_court_days_skip_holidays(self):
        self.assertEqual(compute_due_date(FRI, 3, day_mode="Court days", holidays={date(2026, 11, 23)}), date(2026, 11, 26))

    def test_vacation_days_not_counted_when_flagged(self):
        vac = {date(2026, 11, 18), date(2026, 11, 19)}
        self.assertEqual(compute_due_date(MON, 5, vacations=vac, skip_vacations=True), date(2026, 11, 23))

    def test_vacation_days_ignored_when_not_flagged(self):
        vac = {date(2026, 11, 18), date(2026, 11, 19)}
        self.assertEqual(compute_due_date(MON, 5, vacations=vac, skip_vacations=False), date(2026, 11, 21))

    def test_month_end_clamps(self):
        self.assertEqual(add_months(date(2026, 1, 31), 1), date(2026, 2, 28))

    def test_leap_day_plus_one_year(self):
        self.assertEqual(compute_due_date(date(2024, 2, 29), 1, unit="Years"), date(2025, 2, 28))

    def test_weeks_are_seven_calendar_days(self):
        self.assertEqual(compute_due_date(MON, 2, unit="Weeks"), date(2026, 11, 30))

    def test_before_counts_backwards(self):
        self.assertEqual(compute_due_date(date(2026, 11, 30), 7, direction="Before"), date(2026, 11, 23))

    def test_zero_period_returns_trigger(self):
        self.assertEqual(compute_due_date(MON, 0), MON)

    def test_negative_period_is_rejected(self):
        with self.assertRaises(ValueError):
            compute_due_date(MON, -1)

    def test_court_days_with_weeks_is_rejected(self):
        with self.assertRaises(ValueError):
            compute_due_date(MON, 1, unit="Weeks", day_mode="Court days")

    def test_reminders_fire_at_each_offset_once(self):
        offs = [{"days_before": n, "recipient": "Both"} for n in (30, 14, 7, 1)]
        due = date(2026, 12, 10)
        self.assertEqual([r["days_before"] for r in reminders_due(due, offs, date(2026, 11, 26), [])], [30, 14])
        self.assertEqual([r["days_before"] for r in reminders_due(due, offs, date(2026, 11, 26), [30])], [14])

    def test_no_reminders_once_overdue(self):
        offs = [{"days_before": 1, "recipient": "Both"}]
        self.assertEqual(reminders_due(date(2026, 11, 1), offs, date(2026, 11, 5), []), [])
