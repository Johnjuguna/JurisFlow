import frappe

from jurisflow.services import conflict_service as svc


@frappe.whitelist()
def run_conflict_search(name):
	return svc.run_search(name)


@frappe.whitelist()
def clear_conflict(name, notes):
	return svc.decide(name, "Cleared by Partner", notes)


@frappe.whitelist()
def decline_conflict(name, notes):
	return svc.decide(name, "Declined", notes)


@frappe.whitelist()
def create_customer(name):
	return svc.create_customer(name)
