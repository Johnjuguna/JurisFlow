"""Custom fields JurisFlow adds to ERPNext DocTypes. Idempotent: safe to run on every migrate."""

from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

FIELDS = {
    "Sales Invoice": [
        {
            "fieldname": "matter",
            "label": "Legal Matter",
            "fieldtype": "Link",
            "options": "Legal Matter",
            "insert_after": "customer_name",
            "in_standard_filter": 1,
            "allow_on_submit": 0,
            "description": "The matter this invoice bills for. Shown on the JurisFlow Fee Note.",
        },
    ],
}


def ensure_custom_fields():
    create_custom_fields(FIELDS, update=True)
