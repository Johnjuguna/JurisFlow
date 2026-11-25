import unittest
from datetime import date
from typing import ClassVar

from jurisflow.engines.deadline_calc import add_months, compute_due_date, compute_with_trace, reminders_due

FRI = date(2026, 11, 20)
VAC = {date(2026, 11, d) for d in range(23, 28)}


class TestMonths(unittest.TestCase):
	def test_month_end_clamps_non_leap(self):
		self.assertEqual(add_months(date(2025, 1, 31), 1), date(2025, 2, 28))

	def test_month_end_clamps_leap(self):
		self.assertEqual(add_months(date(2024, 1, 31), 1), date(2024, 2, 29))

	def test_leap_day_plus_one_year(self):
		self.assertEqual(compute_due_date(date(2024, 2, 29), 1, "Years"), date(2025, 2, 28))

	def test_three_months_from_month_end(self):
		self.assertEqual(compute_due_date(date(2026, 11, 30), 3, "Months"), date(2027, 2, 28))


class TestDayCounting(unittest.TestCase):
	def test_calendar_days_day_after_trigger(self):
		self.assertEqual(compute_due_date(FRI, 14), date(2026, 12, 4))

	def test_zero_period_returns_trigger(self):
		self.assertEqual(compute_due_date(FRI, 0), FRI)

	def test_court_day_crosses_weekend_and_holiday(self):
		due = compute_due_date(FRI, 1, "Days", "Court days", holidays={date(2026, 11, 23)})
		self.assertEqual(due, date(2026, 11, 24))

	def test_same_day_start_counts_trigger(self):
		due = compute_due_date(FRI, 1, "Days", "Court days", count_start="Same day")
		self.assertEqual(due, FRI)

	def test_direction_before(self):
		self.assertEqual(compute_due_date(date(2026, 12, 7), 7, direction="Before"), date(2026, 11, 30))


class TestRollingAndVacations(unittest.TestCase):
	def test_roll_next_working_day_reports_original(self):
		t = compute_with_trace(FRI, 1, roll="Next working day")
		self.assertEqual(
			(t["unrolled"], t["due"], t["rolled"]), (date(2026, 11, 21), date(2026, 11, 23), True)
		)

	def test_roll_previous_working_day(self):
		self.assertEqual(compute_due_date(FRI, 1, roll="Previous working day"), FRI)

	def test_roll_skips_holiday_monday(self):
		due = compute_due_date(FRI, 1, roll="Next working day", holidays={date(2026, 11, 23)})
		self.assertEqual(due, date(2026, 11, 24))

	def test_no_roll_flag_when_unmoved(self):
		self.assertFalse(compute_with_trace(FRI, 14)["rolled"])

	def test_vacation_days_not_counted_when_skipped(self):
		self.assertEqual(compute_due_date(FRI, 3, vacations=VAC, skip_vacations=True), date(2026, 11, 28))

	def test_vacation_ignored_when_not_skipped(self):
		self.assertEqual(compute_due_date(FRI, 3, vacations=VAC, skip_vacations=False), date(2026, 11, 23))

	def test_roll_lands_after_vacation(self):
		due = compute_due_date(FRI, 3, vacations=VAC, skip_vacations=True, roll="Next working day")
		self.assertEqual(due, date(2026, 11, 30))


class TestGuards(unittest.TestCase):
	def test_negative_period_rejected(self):
		with self.assertRaises(ValueError):
			compute_due_date(FRI, -1)

	def test_weeks_with_court_days_rejected(self):
		with self.assertRaises(ValueError):
			compute_due_date(FRI, 2, "Weeks", "Court days")

	def test_unknown_unit_rejected(self):
		with self.assertRaises(ValueError):
			compute_due_date(FRI, 2, "Fortnights")

	def test_step_limit_is_enforced(self):
		with self.assertRaises(ValueError):
			compute_due_date(FRI, 5, "Days", "Court days", max_steps=3)


class TestReminders(unittest.TestCase):
	OFFSETS: ClassVar[list] = [
		{"days_before": 7, "recipient": "a"},
		{"days_before": 3, "recipient": "a"},
		{"days_before": 1, "recipient": "a"},
	]

	def test_overdue_gets_none(self):
		self.assertEqual(reminders_due(date(2026, 11, 20), self.OFFSETS, date(2026, 11, 25), []), [])

	def test_already_sent_not_repeated(self):
		got = reminders_due(date(2026, 11, 28), self.OFFSETS, date(2026, 11, 25), [7, 3])
		self.assertEqual(got, [])

	def test_late_created_fires_all_eligible_at_once(self):
		# Characterisation test: documents today's behaviour (7 and 3 both fire when 2 days remain).
		got = reminders_due(date(2026, 11, 27), self.OFFSETS, date(2026, 11, 25), [])
		self.assertEqual([r["days_before"] for r in got], [7, 3])
