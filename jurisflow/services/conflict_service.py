"""Conflict-of-interest search, partner decisions, and the gate on opening a matter."""

import frappe
from frappe import _
from frappe.utils import cint, now_datetime

from jurisflow.engines.conflict_matcher import DEFAULT_THRESHOLD, find_matches, name_similarity

SETTINGS = "JF Compliance Settings"
CLEARED = ("No Conflict", "Cleared by Partner")
FINAL = ("No Conflict", "Cleared by Partner", "Declined")
PARTNER_ROLES = {"Law Firm Partner", "System Manager"}

# Expected matches that are recorded but do not stop the matter: (searched as, found in).
INFORMATIONAL = {
    ("Client", "Customer"),                  # an existing client coming back
    ("Client", "Prior check (client)"),      # the same prospect checked before
    ("Adverse", "Matter (adverse party)"),   # we already act against this party elsewhere
    ("Adverse", "Prior check (adverse)"),
}


def gate_enabled():
    val = frappe.db.get_single_value(SETTINGS, "enforce_conflict_gate")
    return True if val is None else bool(cint(val))


def match_threshold():
    pct = cint(frappe.db.get_single_value(SETTINGS, "name_match_threshold"))
    return (pct / 100) if pct else DEFAULT_THRESHOLD


def require_partner():
    if not (set(frappe.get_roles()) & PARTNER_ROLES):
        frappe.throw(_("Only a Law Firm Partner can clear or decline a conflict."), frappe.PermissionError)


def gather_candidates(exclude_check=None):
    rows = []
    for c in frappe.get_all("Customer", fields=["name", "customer_name", "tax_id"]):
        rows.append({"source": "Customer", "record": c.name, "name": c.customer_name,
                     "id_number": c.tax_id, "role": "Client"})

    for p in frappe.db.sql(
        "select parent, party_name, id_number, role from `tabMatter Party` where parenttype = 'Legal Matter'",
        as_dict=True,
    ):
        rows.append({"source": "Matter Party", "record": p.parent, "name": p.party_name,
                     "id_number": p.id_number, "role": p.role, "matter": p.parent})

    for m in frappe.get_all("Legal Matter", filters={"opposing_party": ["is", "set"]},
                            fields=["name", "opposing_party"]):
        rows.append({"source": "Matter (adverse party)", "record": m.name, "name": m.opposing_party,
                     "role": "Adverse party", "matter": m.name})

    for k in frappe.get_all(
        "Conflict Check", filters={"name": ["!=", exclude_check or ""]},
        fields=["name", "party_name", "id_number", "adverse_party", "other_names", "status"],
    ):
        base = {"record": k.name, "role": f"Check: {k.status}"}
        rows.append({**base, "source": "Prior check (client)", "name": k.party_name, "id_number": k.id_number})
        if k.adverse_party:
            rows.append({**base, "source": "Prior check (adverse)", "name": k.adverse_party})
        for line in (k.other_names or "").splitlines():
            if line.strip():
                rows.append({**base, "source": "Prior check (related)", "name": line.strip()})
    return rows


def search_terms(doc):
    terms = [("Client", doc.party_name, doc.id_number)]
    for line in (doc.other_names or "").splitlines():
        if line.strip():
            terms.append(("Related", line.strip(), None))
    if (doc.adverse_party or "").strip():
        terms.append(("Adverse", doc.adverse_party.strip(), None))
    return terms


def _save(doc):
    doc.flags.via_service = True
    doc.save()


def run_search(name):
    doc = frappe.get_doc("Conflict Check", name)
    if doc.status in FINAL:
        frappe.throw(_("This check is already decided ({0}).").format(doc.status))

    candidates = gather_candidates(exclude_check=doc.name)
    threshold = match_threshold()
    doc.set("hits", [])
    blocking = 0
    for kind, term, ident in search_terms(doc):
        for h in find_matches(term, ident, candidates, threshold):
            blocks = (kind, h["source"]) not in INFORMATIONAL
            blocking += int(blocks)
            doc.append("hits", {
                "term_type": kind, "term": term, "source": h["source"], "record": h["record"],
                "matched_name": h["name"], "role": h["role"], "matter": h["matter"],
                "score": round(h["score"] * 100, 1), "reason": h["reason"], "blocking": int(blocks),
            })

    doc.hit_count = len(doc.hits)
    doc.status = "Conflict Found" if blocking else "No Conflict"
    doc.run_by = frappe.session.user
    doc.run_on = now_datetime()
    _save(doc)
    return doc.status


def decide(name, status, notes):
    require_partner()
    if not (notes or "").strip():
        frappe.throw(_("Please record the reason for this decision."))
    doc = frappe.get_doc("Conflict Check", name)
    if doc.status != "Conflict Found":
        frappe.throw(_("Only a check with conflicts found can be cleared or declined."))
    doc.clearance_notes = notes.strip()
    doc.cleared_by = frappe.session.user
    doc.cleared_on = now_datetime()
    doc.status = status
    _save(doc)
    return doc.status


def create_customer(name):
    doc = frappe.get_doc("Conflict Check", name)
    doc.check_permission("write")
    if doc.status not in CLEARED:
        frappe.throw(_("A Customer can only be created once the conflict check is clear."))
    if doc.customer:
        return doc.customer

    client_name = doc.party_name.strip()
    customer = frappe.db.get_value("Customer", {"customer_name": client_name})
    if not customer:
        cust = frappe.get_doc({
            "doctype": "Customer",
            "customer_name": client_name,
            "customer_type": doc.party_type,
            "customer_group": frappe.db.get_single_value("Selling Settings", "customer_group") or "All Customer Groups",
            "territory": frappe.db.get_single_value("Selling Settings", "territory") or "All Territories",
            "tax_id": doc.id_number or None,  # so future conflict searches can match on it
        }).insert(ignore_permissions=True)
        customer = cust.name

    doc.customer = customer
    _save(doc)
    return customer


def enforce_gate(doc, method=None):
    """doc_events validate hook for Legal Matter."""
    if not gate_enabled():
        return
    if not (doc.is_new() or doc.has_value_changed("conflict_check")):
        return

    if not doc.get("conflict_check"):
        frappe.throw(_("A cleared Conflict Check is required before a matter can be opened."),
                     title=_("Conflict Check required"))

    check = frappe.db.get_value(
        "Conflict Check", doc.conflict_check, ["status", "customer", "adverse_party"], as_dict=True
    )
    if not check:
        frappe.throw(_("Conflict Check {0} does not exist.").format(doc.conflict_check))
    if check.status not in CLEARED:
        frappe.throw(_("Conflict Check {0} is '{1}'. It must be clear, or cleared by a partner, first.").format(
            doc.conflict_check, check.status), title=_("Conflict Check not clear"))
    if check.customer and check.customer != doc.customer:
        frappe.throw(_("Conflict Check {0} was cleared for a different client.").format(doc.conflict_check))

    used = frappe.db.get_value(
        "Legal Matter", {"conflict_check": doc.conflict_check, "name": ["!=", doc.name or ""]}, "name"
    )
    if used:
        frappe.throw(_("Conflict Check {0} is already used by matter {1}. Run a new check for this matter.").format(
            doc.conflict_check, used))

    opposing = (doc.get("opposing_party") or "").strip()
    if opposing and name_similarity(opposing, check.adverse_party or "") < match_threshold():
        frappe.throw(_("The opposing party ({0}) was not covered by Conflict Check {1}. "
                       "Run a new check that includes it.").format(opposing, doc.conflict_check))
