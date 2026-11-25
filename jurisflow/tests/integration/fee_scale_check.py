import frappe

from jurisflow.engines.fee_scale_calc import compute_scale_fee
from jurisflow.tests.unit.test_fee_scale_calc import BANDS


def say(label, ok, extra=""):
	print(("PASS  " if ok else "FAIL  ") + label, extra)


def run():
	frappe.set_user("Administrator")
	name = "ZZ TEST SCALE"
	frappe.delete_doc("Fee Scale", name, force=1, ignore_missing=True)
	doc = frappe.get_doc(
		{
			"doctype": "Fee Scale",
			"scale_name": name,
			"effective_from": "2026-01-01",
			"source_reference": "TEST ONLY - not a gazetted schedule",
			"bands": BANDS,
		}
	).insert()
	say("fee scale saved", bool(doc.name))
	fee = compute_scale_fee([b.as_dict() for b in doc.bands], 200000)[0]
	say("fee from saved bands = 15000", float(fee) == 15000.0, fee)
	try:
		frappe.get_doc(
			{
				"doctype": "Fee Scale",
				"scale_name": name + "2",
				"effective_from": "2026-01-01",
				"source_reference": "x",
				"bands": [BANDS[0]],
			}
		).insert()
		say("bad bands refused", False)
	except frappe.ValidationError:
		say("bad bands refused", True)
	frappe.delete_doc("Fee Scale", name, force=1)
