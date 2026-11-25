"""Scale fee maths. Pure Python so it is unit-testable. Bands come from a Fee Scale record."""

from decimal import ROUND_HALF_UP, Decimal


def _d(x):
	return Decimal(str(x or 0))


def _sorted(bands):
	return sorted(bands, key=lambda b: _d(b["from_value"]))


def validate_bands(bands):
	if not bands:
		return ["At least one band is required."]
	rows, errors = _sorted(bands), []
	if _d(rows[0]["from_value"]) != 0:
		errors.append("The first band must start at 0.")
	for i, b in enumerate(rows):
		lo, hi, last = _d(b["from_value"]), _d(b["to_value"]), i == len(rows) - 1
		if last and hi != 0:
			errors.append("The last band must be open-ended (To Value 0).")
		if not last:
			if hi == 0:
				errors.append(f"Only the last band can be open-ended (band from {lo}).")
			elif hi <= lo:
				errors.append(f"Band from {lo}: To Value must be greater than From Value.")
			elif _d(rows[i + 1]["from_value"]) != hi:
				errors.append(
					f"Bands must be contiguous: band ending {hi} is not followed by a band starting {hi}."
				)
	return errors


def compute_scale_fee(bands, value, minimum=0):
	"""Return (fee, trace). trace is a list of dicts, one per band reached."""
	value = _d(value)
	if value < 0:
		raise ValueError("Value cannot be negative.")
	errors = validate_bands(bands)
	if errors:
		raise ValueError("; ".join(errors))
	total, trace = Decimal(0), []
	for b in _sorted(bands):
		lo, hi = _d(b["from_value"]), _d(b["to_value"])
		if value <= lo:
			break
		portion = (min(value, hi) if hi else value) - lo
		amount = _d(b.get("fixed_amount")) + portion * _d(b.get("rate_percent")) / 100
		total += amount
		trace.append(
			{
				"from": lo,
				"to": hi,
				"portion": portion,
				"rate_percent": _d(b.get("rate_percent")),
				"fixed": _d(b.get("fixed_amount")),
				"amount": amount,
			}
		)
	fee = max(total, _d(minimum)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
	return fee, trace
