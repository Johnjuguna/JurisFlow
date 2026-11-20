import json
import pathlib

import frappe


def execute():
    cfg = json.loads((pathlib.Path(frappe.get_app_path("jurisflow")) / "config" / "deadline_config.json").read_text())
    for role in cfg["roles"]:
        if not frappe.db.exists("Role", role):
            frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1}).insert(ignore_permissions=True)
