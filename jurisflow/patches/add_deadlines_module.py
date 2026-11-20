import frappe


def execute():
    if not frappe.db.exists("Module Def", "JF Deadlines"):
        frappe.get_doc({"doctype": "Module Def", "module_name": "JF Deadlines",
                        "app_name": "jurisflow"}).insert(ignore_permissions=True)
