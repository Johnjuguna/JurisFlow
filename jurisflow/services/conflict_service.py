"""Conflict-of-interest search, partner decisions, and the gate on opening a matter."""

import frappe
from frappe import _
from frappe.utils import escape_html, formatdate, getdate, now_datetime, today

from jurisflow.engines.conflict_gate import (
    clearance_expired,
    same_party,
    split_names,
    uncovered_parties,
    usable_ids,
)
from jurisflow.engines.conflict_matcher import find_matches
from jurisflow.services import conflict_settings

# Statuses of a Conflict Check.
STATUS_FOUND = "Conflict Found"
STATUS_NO_CONFLICT = "No Conflict"
STATUS_CLEARED = "Cleared by Partner"
STATUS_DECLINED = "Declined"
CLEARED = (STATUS_NO_CONFLICT, STATUS_CLEARED)
FINAL = (STATUS_NO_CONFLICT, STATUS_CLEARED, STATUS_DECLINED)
PARTNER_DECISIONS = (STATUS_CLEARED, STATUS_DECLINED)  # the only outcomes a partner can record

# What a name was searched as, and where a match was found. The Select options of
# Conflict Informational Rule must list exactly these; a unit test guards against drift.
KINDS = ("Client", "Related", "Adverse")
SOURCES = (
    "Customer",
    "Matter Party",
    "Matter (adverse party)",
    "Prior check (client)",
    "Prior check (adverse)",
    "Prior check (related)",
)
SRC_CUSTOMER, SRC_PARTY, SRC_MATTER_ADVERSE, SRC_CHECK_CLIENT, SRC_CHECK_ADVERSE, SRC_CHECK_RELATED = SOURCES

PARTY_DOCTYPE = "Matter Party"


# --- permissions -----------------------------------------------------------------------------

def require_partner():
    allowed = conflict_settings.partner_roles()
    if not allowed:
        frappe.throw(_("No roles are allowed to clear conflicts yet. Set them in JF Compliance Settings."))
    if not (set(frappe.get_roles()) & allowed):
        frappe.throw(_("You are not permitted to clear or decline a conflict."), frappe.PermissionError)


# --- search ----------------------------------------------------------------------------------

def gather_candidates(exclude_check=None):
    rows = []
    for c in frappe.get_all("Customer", fields=["name", "customer_name", "tax_id"]):
        rows.append({"source": SRC_CUSTOMER, "record": c.name, "name": c.customer_name,
                     "id_number": c.tax_id, "role": "Client"})

    for p in frappe.db.sql(
        "select parent, party_name, id_number, role from `tabMatter Party` where parenttype = 'Legal Matter'",
        as_dict=True,
    ):
        rows.append({"source": SRC_PARTY, "record": p.parent, "name": p.party_name,
                     "id_number": p.id_number, "role": p.role, "matter": p.parent})

    for m in frappe.get_all("Legal Matter", filters={"opposing_party": ["is", "set"]},
                            fields=["name", "opposing_party"]):
        rows.append({"source": SRC_MATTER_ADVERSE, "record": m.name, "name": m.opposing_party,
                     "role": "Adverse party", "matter": m.name})

    for k in frappe.get_all(
        "Conflict Check", filters={"name": ["!=", exclude_check or ""]},
        fields=["name", "party_name", "id_number", "adverse_party", "other_names", "status"],
    ):
        base = {"record": k.name, "role": f"Check: {k.status}"}
        rows.append({**base, "source": SRC_CHECK_CLIENT, "name": k.party_name, "id_number": k.id_number})
        if k.adverse_party:
            rows.append({**base, "source": SRC_CHECK_ADVERSE, "name": k.adverse_party})
        for name in split_names(k.other_names):
            rows.append({**base, "source": SRC_CHECK_RELATED, "name": name})
    return rows


def search_terms(doc):
    terms = [("Client", doc.party_name, doc.id_number)]
    for name in split_names(doc.other_names):
        terms.append(("Related", name, None))
    if (doc.adverse_party or "").strip():
        terms.append(("Adverse", doc.adverse_party.strip(), None))
    return terms


def _save(doc):
    doc.flags.via_service = True
    doc.save()


def run_search(name):
    doc = frappe.get_doc("Conflict Check", name)
    doc.check_permission("write")
    if doc.status in FINAL:
        frappe.throw(_("This check is already decided ({0}).").format(doc.status))

    candidates = gather_candidates(exclude_check=doc.name)
    threshold = conflict_settings.match_threshold()
    informational = conflict_settings.informational_pairs()
    doc.set("hits", [])
    blocking = 0
    for kind, term, ident in search_terms(doc):
        for h in find_matches(term, ident, candidates, threshold):
            blocks = (kind, h["source"]) not in informational
            blocking += int(blocks)
            doc.append("hits", {
                "term_type": kind, "term": term, "source": h["source"], "record": h["record"],
                "matched_name": h["name"], "role": h["role"], "matter": h["matter"],
                "score": round(h["score"] * 100, 1), "reason": h["reason"], "blocking": int(blocks),
            })

    doc.hit_count = len(doc.hits)
    doc.status = STATUS_FOUND if blocking else STATUS_NO_CONFLICT
    doc.run_by = frappe.session.user
    doc.run_on = now_datetime()
    _save(doc)
    return doc.status


def decide(name, status, notes):
    doc = frappe.get_doc("Conflict Check", name)
    doc.check_permission("write")
    require_partner()
    if status not in PARTNER_DECISIONS:
        frappe.throw(_("A decision must be one of: {0}.").format(", ".join(PARTNER_DECISIONS)))
    if not (notes or "").strip():
        frappe.throw(_("Please record the reason for this decision."))
    if doc.status != STATUS_FOUND:
        frappe.throw(_("Only a check with conflicts found can be cleared or declined."))
    doc.clearance_notes = notes.strip()
    doc.cleared_by = frappe.session.user
    doc.cleared_on = now_datetime()
    doc.status = status
    _save(doc)
    return doc.status


def _default_leaf(doctype, setting_field):
    """The Selling Settings default if it is a real (non-group) record, else the first real one.
    Group records such as 'All Customer Groups' cannot be attached to a Customer."""
    value = frappe.db.get_single_value("Selling Settings", setting_field)
    if value and not frappe.db.get_value(doctype, value, "is_group"):
        return value
    leaf = frappe.db.get_value(doctype, {"is_group": 0}, "name", order_by="lft asc")
    if not leaf:
        frappe.throw(_("Create a {0} that is not a group, or set a default in Selling Settings.").format(_(doctype)))
    return leaf


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
            "customer_group": _default_leaf("Customer Group", "customer_group"),
            "territory": _default_leaf("Territory", "territory"),
            "tax_id": doc.id_number or None,  # so future conflict searches can match on it
        }).insert(ignore_permissions=True)
        customer = cust.name

    doc.customer = customer
    _save(doc)
    return customer


# --- the gate on Legal Matter ----------------------------------------------------------------

def _party_rows(doc):
    """Rows of every child table on the document that holds Matter Parties."""
    rows = []
    for df in frappe.get_meta(doc.doctype).get_table_fields():
        if df.options == PARTY_DOCTYPE:
            rows.extend(doc.get(df.fieldname) or [])
    return rows


def _party_signature(doc):
    return sorted(
        ((r.get("party_name") or "").strip().casefold(), (r.get("id_number") or "").strip().casefold(),
         (r.get("role") or "").strip().casefold())
        for r in _party_rows(doc)
    )


def _coverage_inputs_changed(doc):
    """Has anything the check is supposed to cover changed since the last save?"""
    before = doc.get_doc_before_save()
    if not before:
        return True
    if doc.has_value_changed("customer") or doc.has_value_changed("opposing_party"):
        return True
    return _party_signature(doc) != _party_signature(before)


def _load_check(name):
    check = frappe.db.get_value(
        "Conflict Check", name,
        ["status", "customer", "party_name", "id_number", "adverse_party", "other_names", "run_on", "cleared_on"],
        as_dict=True,
    )
    if not check:
        frappe.throw(_("Conflict Check {0} does not exist.").format(name))
    return check


def _names(items):
    return ", ".join(frappe.bold(escape_html(i["name"])) for i in items)


def _enforce_freshness(doc, check):
    """Rules that apply when a check is attached to a matter, not on every later save."""
    days = conflict_settings.clearance_validity_days()
    decided = check.cleared_on or check.run_on
    if clearance_expired(getdate(decided) if decided else None, getdate(today()), days):
        frappe.throw(
            _("Conflict Check {0} was decided on {1}, which is more than {2} days ago. Run a new check.").format(
                doc.conflict_check, formatdate(decided) if decided else _("an unknown date"), days),
            title=_("Conflict Check expired"),
        )

    used = frappe.db.get_value(
        "Legal Matter", {"conflict_check": doc.conflict_check, "name": ["!=", doc.name or ""]}, "name"
    )
    if used:
        frappe.throw(_("Conflict Check {0} is already used by matter {1}. Run a new check for this matter.").format(
            doc.conflict_check, used))


def _enforce_client(doc, check, threshold):
    if not doc.get("customer"):
        return
    if check.customer:
        if check.customer != doc.customer:
            frappe.throw(_("Conflict Check {0} was cleared for a different client.").format(doc.conflict_check))
        return
    # The check was cleared before a Customer existed, so compare by identifier or name.
    cust = frappe.db.get_value("Customer", doc.customer, ["customer_name", "tax_id"], as_dict=True)
    if cust and not same_party(cust.customer_name, cust.tax_id, check.party_name, check.id_number, threshold):
        frappe.throw(_("Conflict Check {0} was cleared for a different client.").format(doc.conflict_check))


def _enforce_parties(doc, check, threshold):
    adverse_names = [n for n in [check.adverse_party, *split_names(check.other_names)] if (n or "").strip()]
    all_names = [check.party_name, *adverse_names]
    check_ids = usable_ids(check.id_number)

    # The opposing party must have been searched as an adverse (or related) name.
    opposing = [{"name": (doc.get("opposing_party") or "").strip()}]
    gaps = uncovered_parties(opposing, adverse_names, set(), threshold)

    # Every other party on the matter must be somewhere in the check, unless its role is exempt.
    parties = [
        {"name": r.get("party_name"), "id_number": r.get("id_number"), "role": r.get("role")}
        for r in _party_rows(doc)
    ]
    gaps += uncovered_parties(parties, all_names, check_ids, threshold,
                              exempt_roles=conflict_settings.exempt_party_roles())
    if gaps:
        frappe.throw(
            _("These parties were not covered by Conflict Check {0}: {1}. Run a new check that includes them.").format(
                doc.conflict_check, _names(gaps)),
            title=_("Parties not covered"),
        )


def enforce_gate(doc, method=None):
    """doc_events validate hook for Legal Matter.

    Opening a matter (new, or a different check attached) applies every rule. Any later save
    re-checks only that the check still covers the client and parties, if those changed.
    """
    if not conflict_settings.gate_enabled():
        return
    opening = doc.is_new() or doc.has_value_changed("conflict_check")
    if not (opening or _coverage_inputs_changed(doc)):
        return

    if not doc.get("conflict_check"):
        frappe.throw(_("A cleared Conflict Check is required before a matter can be opened."),
                     title=_("Conflict Check required"))

    check = _load_check(doc.conflict_check)
    if check.status not in CLEARED:
        frappe.throw(_("Conflict Check {0} is '{1}'. It must be clear, or cleared by a partner, first.").format(
            doc.conflict_check, check.status), title=_("Conflict Check not clear"))

    threshold = conflict_settings.match_threshold()
    if opening:
        _enforce_freshness(doc, check)
    _enforce_client(doc, check, threshold)
    _enforce_parties(doc, check, threshold)
