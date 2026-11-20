import frappe


def make_cleared_check():
    """A Conflict Check on a unique name, searched and clear. Returns its name."""
    from jurisflow.services.conflict_service import run_search

    doc = frappe.get_doc({
        "doctype": "Conflict Check", "party_type": "Company",
        "party_name": f"ZQ{frappe.generate_hash(length=12)}",
    }).insert()
    status = run_search(doc.name)
    assert status == "No Conflict", status
    return doc.name
