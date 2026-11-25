import unittest
from datetime import date, datetime, timedelta

from jurisflow.engines.hearing_clock import hearing_moment, next_court_day, seconds_of


class TestHearingClock(unittest.TestCase):
	def test_seconds_of(self):
		self.assertIsNone(seconds_of(None))
		self.assertIsNone(seconds_of(""))
		self.assertEqual(seconds_of("09:30:00"), 34200)
		self.assertEqual(seconds_of(timedelta(hours=14)), 50400)

	def test_hearing_moment_defaults_to_nine(self):
		self.assertEqual(hearing_moment(date(2026, 11, 20), None), datetime(2026, 11, 20, 9, 0))

	def test_next_court_day_skips_weekend(self):
		self.assertEqual(next_court_day(date(2026, 11, 13)), date(2026, 11, 16))  # Fri -> Mon

	def test_next_court_day_skips_holiday(self):
		self.assertEqual(next_court_day(date(2026, 12, 24), {date(2026, 12, 25)}), date(2026, 12, 28))
