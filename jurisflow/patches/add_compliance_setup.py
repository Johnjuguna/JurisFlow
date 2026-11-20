import frappe

from jurisflow.setup.install import ensure_roles


def execute():
    if not frappe.db.exists("Module Def", "JF Compliance"):
        frappe.get_doc(
            {"doctype": "Module Def", "module_name": "JF Compliance", "app_name": "jurisflow"}
        ).insert(ignore_permissions=True)
    ensure_roles()
