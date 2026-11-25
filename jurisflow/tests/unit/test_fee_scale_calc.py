from decimal import Decimal
import pytest
from jurisflow.engines.fee_scale_calc import compute_scale_fee, validate_bands

# Made-up bands for testing only. These are NOT remuneration order figures.
BANDS = [
    {"from_value": 0, "to_value": 100000, "rate_percent": 10, "fixed_amount": 0},
    {"from_value": 100000, "to_value": 500000, "rate_percent": 5, "fixed_amount": 0},
    {"from_value": 500000, "to_value": 0, "rate_percent": 2, "fixed_amount": 1000},
]


def test_inside_first_band():
    assert compute_scale_fee(BANDS, 50000)[0] == Decimal("5000.00")


def test_boundary_exact():
    assert compute_scale_fee(BANDS, 100000)[0] == Decimal("10000.00")


def test_two_bands():
    assert compute_scale_fee(BANDS, 200000)[0] == Decimal("15000.00")


def test_open_ended_with_fixed():
    assert compute_scale_fee(BANDS, 600000)[0] == Decimal("33000.00")


def test_minimum_applies():
    assert compute_scale_fee(BANDS, 50000, minimum=8000)[0] == Decimal("8000.00")


def test_zero_value_gives_minimum():
    assert compute_scale_fee(BANDS, 0, minimum=500)[0] == Decimal("500.00")


def test_trace_has_one_row_per_band_reached():
    assert len(compute_scale_fee(BANDS, 200000)[1]) == 2


def test_negative_rejected():
    with pytest.raises(ValueError):
        compute_scale_fee(BANDS, -1)


def test_gap_rejected():
    bad = [dict(BANDS[0]), {**BANDS[1], "from_value": 120000}, BANDS[2]]
    assert validate_bands(bad)


def test_must_start_at_zero_and_end_open():
    assert validate_bands([{"from_value": 10, "to_value": 100, "rate_percent": 1}])
