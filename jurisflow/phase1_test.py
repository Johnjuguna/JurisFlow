import frappe
from frappe.utils import add_days, today


def say(label, ok, extra=""):
    print(("PASS  " if ok else "FAIL  ") + label, extra)


def run():
    frappe.set_user("Administrator")

    for n, lvl, st in [("Milimani Law Courts", "High Court", "Nairobi"),
                       ("Kibera Law Courts", "Magistrate's Court", "Nairobi")]:
        if not frappe.db.exists("Court", n):
            frappe.get_doc({"doctype": "Court", "court_name": n, "court_level": lvl, "station": st}).insert()

    customer = frappe.db.get_value("Customer", {}, "name")
    if not customer:
        customer = frappe.get_doc(
            {"doctype": "Customer", "customer_name": "Test Client Ltd", "customer_type": "Company"}
        ).insert().name

    m = frappe.get_doc({
        "doctype": "Legal Matter", "title": "TEST Client v Test Opponent", "customer": customer,
        "court": "Milimani Law Courts", "case_no": "HCCC E001 of 2026",
        "responsible_advocate": "Administrator", "status": "Open",
    }).insert()
    print("Matter:", m.name)

    h1 = frappe.get_doc({"doctype": "Court Hearing", "matter": m.name, "hearing_date": add_days(today(), 1),
                         "hearing_time": "09:00:00", "purpose": "Mention"}).insert()
    say("court and advocate default from matter",
        h1.court == "Milimani Law Courts" and h1.attending_advocate == "Administrator")

    frappe.local.message_log = []
    frappe.get_doc({"doctype": "Court Hearing", "matter": m.name, "hearing_date": add_days(today(), 1),
                    "hearing_time": "09:00:00", "purpose": "Hearing"}).insert()
    say("clash warning shown", any("Clash" in str(x) for x in frappe.local.message_log))

    say("matter next hearing set",
        str(frappe.db.get_value("Legal Matter", m.name, "next_hearing_date")) == str(add_days(today(), 1)))

    try:
        h1.status = "Adjourned"
        h1.save()
        say("future hearing cannot be adjourned", False)
    except frappe.ValidationError:
        say("future hearing cannot be adjourned", True)

    try:
        mm = frappe.get_doc("Legal Matter", m.name)
        mm.status = "Closed"
        mm.save()
        say("cannot close matter with scheduled hearings", False)
    except frappe.ValidationError:
        say("cannot close matter with scheduled hearings", True)

    h3 = frappe.get_doc({"doctype": "Court Hearing", "matter": m.name, "hearing_date": add_days(today(), -3),
                         "purpose": "Mention", "status": "Scheduled"}).insert()
    h3.status = "Adjourned"
    try:
        h3.save()
        say("adjourn without reason/next date refused", False)
    except frappe.ValidationError:
        say("adjourn without reason/next date refused", True)

    h3.reload()
    h3.status = "Adjourned"
    h3.reload()
    h3.status = "Adjourned"
    h3.adjournment_reason = "Court not sitting"
    h3.next_date = add_days(today(), 30)
    h3.save()
    nxt = frappe.db.get_value("Court Hearing", h3.name, "next_hearing")
    ok = bool(nxt) and str(frappe.db.get_value("Court Hearing", nxt, "hearing_date")) == str(add_days(today(), 30))
    say("next hearing auto-created", ok, nxt or "")

    frappe.get_doc({"doctype": "Legal Time Entry", "matter": m.name, "advocate": "Administrator",
                    "entry_date": today(), "hours": 2, "rate": 5000, "billable": 1,
                    "narration": "Drafting"}).insert()
    frappe.get_doc({"doctype": "Matter Task", "matter": m.name, "subject": "Limitation expiry",
                    "task_type": "Limitation Date", "due_date": add_days(today(), 90),
                    "status": "Open"}).insert()
    vals = frappe.db.get_value("Legal Matter", m.name, ["unbilled_amount", "limitation_date"], as_dict=True)
    say("unbilled amount = 10000", float(vals.unbilled_amount or 0) == 10000, str(vals.unbilled_amount))
    say("limitation date set", str(vals.limitation_date) == str(add_days(today(), 90)), str(vals.limitation_date))

    from jurisflow.court_jobs import escalate_unconfirmed_hearings, send_daily_court_brief
    try:
        send_daily_court_brief()
        escalate_unconfirmed_hearings()
        say("scheduled jobs run without error", True)
    except Exception as e:
        say("scheduled jobs run without error", False, repr(e))

    from jurisflow.jurisflow.report.matters_without_next_action.matters_without_next_action import execute
    cols, data = execute()
    say("report runs", isinstance(data, list), f"{len(data)} row(s)")

    frappe.db.commit()
    print("\nTest matter left in place:", m.name, "(delete it from the Legal Matter list when done)")
