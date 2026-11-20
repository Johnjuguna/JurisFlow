import frappe

ROLES = ["Advocate", "Law Clerk", "Legal Admin", "Law Firm Partner"]
AREAS = ["Litigation", "Conveyancing", "Corporate and Commercial",
         "Family", "Probate and Succession", "Employment"]


def ensure_roles():
    for r in ROLES:
        if not frappe.db.exists("Role", r):
            frappe.get_doc({"doctype": "Role", "role_name": r, "desk_access": 1}).insert(ignore_permissions=True)
    frappe.db.commit()


def seed_areas():
    for a in AREAS:
        if not frappe.db.exists("Practice Area", a):
            frappe.get_doc({"doctype": "Practice Area", "area_name": a}).insert(ignore_permissions=True)
    frappe.db.commit()


def after_install():
    ensure_roles()
    seed_areas()
