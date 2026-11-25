import frappe

MODULES = ["JF Matters", "JF Diary", "JF Billing"]


def execute():
	for m in MODULES:
		if not frappe.db.exists("Module Def", m):
			frappe.get_doc({"doctype": "Module Def", "module_name": m, "app_name": "jurisflow"}).insert(
				ignore_permissions=True
			)
