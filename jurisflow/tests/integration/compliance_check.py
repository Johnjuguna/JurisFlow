import frappe

from jurisflow.services import conflict_service as svc


def say(label, ok, extra=""):
	print(("PASS  " if ok else "FAIL  ") + label, extra)


def refused(fn):
	try:
		fn()
	except frappe.ValidationError:
		return True
	return False


def unique(prefix):
	return f"{prefix}{frappe.generate_hash(length=12)}"


def matter_doc(**kw):
	m = frappe.new_doc("Legal Matter")
	m.update(kw)
	return m


def run():
	frappe.set_user("Administrator")
	checks, customers = [], []

	def new_check(**kw):
		kw.setdefault("party_type", "Company")
		doc = frappe.get_doc({"doctype": "Conflict Check", **kw}).insert()
		checks.append(doc.name)
		return doc

	try:
		say("gate is enabled", svc.gate_enabled())

		a = new_check(party_name=unique("ZQ"))
		say("clean search finds no conflict", svc.run_search(a.name) == "No Conflict")

		b = new_check(party_name=unique("ZR"), adverse_party=a.party_name)
		status = svc.run_search(b.name)
		b.reload()
		say(
			"adverse party who was a prior prospect blocks",
			status == "Conflict Found" and any(h.blocking for h in b.hits),
			f"{b.hit_count} match(es)",
		)

		say("matter without a check is refused", refused(lambda: svc.enforce_gate(matter_doc(customer="X"))))
		say(
			"matter with an unresolved check is refused",
			refused(lambda: svc.enforce_gate(matter_doc(conflict_check=b.name, customer="X"))),
		)
		say(
			"clearing without a reason is refused",
			refused(lambda: svc.decide(b.name, "Cleared by Partner", "")),
		)

		svc.decide(b.name, "Cleared by Partner", "Test: prior contact was only a phone enquiry")
		b.reload()
		say(
			"partner clearance recorded", b.status == "Cleared by Partner" and b.cleared_by == "Administrator"
		)

		say(
			"matter with a cleared check passes",
			not refused(
				lambda: svc.enforce_gate(
					matter_doc(conflict_check=b.name, customer="X", opposing_party=a.party_name)
				)
			),
		)
		say(
			"opposing party not covered by the check is refused",
			refused(
				lambda: svc.enforce_gate(
					matter_doc(
						conflict_check=b.name, customer="X", opposing_party="Completely Different Adverse"
					)
				)
			),
		)

		c = new_check(party_name=unique("ZS"))
		c.status = "No Conflict"
		say("editing status by hand is refused", refused(c.save))

		b.party_name = unique("ZT")
		say("changing a decided check is refused", refused(b.save))

		b.reload()
		cust = svc.create_customer(b.name)
		customers.append(cust)
		b.reload()
		say("customer created after clearance", b.customer == cust, cust)
		say(
			"clearance cannot be used for another client",
			refused(
				lambda: svc.enforce_gate(
					matter_doc(conflict_check=b.name, customer="Someone Else", opposing_party=a.party_name)
				)
			),
		)
	finally:
		for n in checks:
			frappe.delete_doc("Conflict Check", n, force=True)
		for n in customers:
			frappe.delete_doc("Customer", n, force=True)
		frappe.db.commit()
	print("\nTest data removed.")
