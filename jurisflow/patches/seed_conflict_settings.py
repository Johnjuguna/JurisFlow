"""One-time seed so existing behaviour survives moving these rules from code into settings.
Only fills tables that are empty; after this the firm owns the values."""

import frappe

SETTINGS = "JF Compliance Settings"

# What the code used to hardcode.
PARTNER_ROLES = ("Law Firm Partner", "System Manager")
INFORMATIONAL = (
    ("Client", "Customer"),
    ("Client", "Prior check (client)"),
    ("Adverse", "Matter (adverse party)"),
    ("Adverse", "Prior check (adverse)"),
)


def execute():
    doc = frappe.get_doc(SETTINGS, SETTINGS)
    if not doc.get("partner_roles"):
        for role in PARTNER_ROLES:
            if frappe.db.exists("Role", role):
                doc.append("partner_roles", {"role": role})
    if not doc.get("informational_rules"):
        for searched_as, found_in in INFORMATIONAL:
            doc.append("informational_rules", {"searched_as": searched_as, "found_in": found_in})
    doc.save(ignore_permissions=True)
