import frappe
from frappe import _
from frappe.utils import flt
from jurisflow.engines.fee_scale_calc import compute_scale_fee


@frappe.whitelist()
def load_time_entries(fee_note):
    fn = frappe.get_doc("Fee Note", fee_note)
    if fn.docstatus != 0:
        frappe.throw(_("Only a draft Fee Note can be changed."))
    rows = frappe.db.sql(
        """select name, entry_date, advocate, narration, hours, rate
        from `tabLegal Time Entry`
        where matter=%s and billable=1 and billed=0 and docstatus=1
        order by entry_date, creation for update""", fn.matter, as_dict=True)
    if not rows:
        frappe.throw(_("No unbilled time entries for this matter."))
    for r in rows:
        fn.append("lines", {
            "line_type": "Fee", "qty": r.hours, "rate": r.rate, "vat_applicable": 1,
            "description": f"{r.entry_date} | {r.advocate} | {r.narration}",
            "time_entry": r.name})
    fn.save()
    return len(rows)


@frappe.whitelist()
def apply_scale_fee(fee_note):
    fn = frappe.get_doc("Fee Note", fee_note)
    if fn.docstatus != 0:
        frappe.throw(_("Only a draft Fee Note can be changed."))
    if not fn.fee_scale or not flt(fn.transaction_value):
        frappe.throw(_("Choose a Fee Scale and enter the Transaction Value."))
    scale = frappe.get_doc("Fee Scale", fn.fee_scale)
    if not scale.is_active:
        frappe.throw(_("Fee Scale {0} is not active.").format(scale.name))
    fee, trace = compute_scale_fee([b.as_dict() for b in scale.bands],
                                   fn.transaction_value, scale.minimum_fee)
    note = "; ".join(f"{t['portion']:,.2f} @ {t['rate_percent']}%" for t in trace)
    fn.append("lines", {
        "line_type": "Fee", "qty": 1, "rate": float(fee), "vat_applicable": 1,
        "description": f"Scale fee ({scale.name}, {scale.source_reference}) on {flt(fn.transaction_value):,.2f}: {note}"})
    fn.save()
    return float(fee)


def on_submit(doc, method=None):
    for r in doc.lines:
        if r.time_entry:
            if frappe.db.get_value("Legal Time Entry", r.time_entry, "billed"):
                frappe.throw(_("Time entry {0} is already billed.").format(r.time_entry))
            frappe.db.set_value("Legal Time Entry", r.time_entry,
                                {"billed": 1}, update_modified=False)
    from jurisflow.services.matter_service import refresh_matter_summary
    refresh_matter_summary(doc.matter, touch=False)


def on_cancel(doc, method=None):
    for r in doc.lines:
        if r.time_entry:
            frappe.db.set_value("Legal Time Entry", r.time_entry,
                                {"billed": 0}, update_modified=False)
    from jurisflow.services.matter_service import refresh_matter_summary
    refresh_matter_summary(doc.matter, touch=False)
