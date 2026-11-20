"""Integration check for JF Deadlines. Run on a scratch site only:
bench --site jftest.local execute jurisflow.tests.integration.deadline_check.run
Rolls back at the end, so it leaves no data."""
import importlib
import json
import pathlib

import frappe

DOCTYPES = ["JF Deadline Settings", "Deadline Rule", "Deadline Trigger Event",
            "Computed Deadline", "Deadline Reminder Offset", "Court Vacation Period",
            "Deadline Verifier Role"]


def run():
    frappe.set_user("Administrator")
    results = []

    def check(name, passed, detail=""):
        results.append(passed)
        print(("PASS  " if passed else "FAIL  ") + name + (f"  [{detail}]" if detail else ""))

    def raises(fn):
        try:
            fn()
        except Exception as e:
            return type(e).__name__
        return None

    for dt in DOCTYPES:
        check(f"doctype exists: {dt}", bool(frappe.db.exists("DocType", dt)))

    cfg = json.loads((pathlib.Path(frappe.get_app_path("jurisflow")) / "config" / "deadline_config.json").read_text())
    for role in cfg["roles"]:
        check(f"role exists: {role}", bool(frappe.db.exists("Role", role)))

    jobs = frappe.get_hooks("scheduler_events").get("cron", {})
    flat = [j for v in jobs.values() for j in (v if isinstance(v, list) else [v])]
    check("deadline job registered in hooks", "jurisflow.jobs.deadline_jobs.run_deadline_checks" in flat)

    for mod in ("jurisflow.jobs.deadline_jobs", "jurisflow.services.deadline_service"):
        err = raises(lambda m=mod: importlib.import_module(m))
        check(f"module imports: {mod}", err is None, err or "")
    hj = importlib.import_module("jurisflow.jobs.hearing_jobs")
    check("hearing_jobs has send and partner_recipients", hasattr(hj, "send") and hasattr(hj, "partner_recipients"))

    # rule lifecycle
    settings = frappe.get_doc("JF Deadline Settings")
    if not settings.verifier_roles:
        settings.append("verifier_roles", {"role": cfg["roles"][1]})
        settings.save(ignore_permissions=True)

    base = {"doctype": "Deadline Rule", "deadline_title": "TEST deadline", "trigger_type": "Filing",
            "period_value": 14, "period_unit": "Days", "statute_reference": "TEST ONLY, not law"}

    err = raises(lambda: frappe.get_doc({**base, "rule_name": "ZZ-TEST-unverified", "active": 1}).insert())
    check("unverified rule cannot be activated", err is not None, err or "no error raised")

    err = raises(lambda: frappe.get_doc({**base, "rule_name": "ZZ-TEST-selfverify",
                                         "verified_by": "Administrator"}).insert())
    check("verification cannot be set directly", err is not None, err or "no error raised")

    err = raises(lambda: frappe.get_doc({**base, "rule_name": "ZZ-TEST-zero", "period_value": 0}).insert())
    check("zero period is rejected", err is not None, err or "no error raised")

    rule = frappe.get_doc({**base, "rule_name": "ZZ-TEST-rule"}).insert()
    from jurisflow.jf_deadlines.doctype.deadline_rule.deadline_rule import verify_rule
    verify_rule(rule.name)
    rule.reload()
    check("verify action sets verifier and date", bool(rule.verified_by and rule.verified_on))
    rule.active = 1
    rule.save()
    check("verified rule can be activated", bool(rule.active))
    rule.period_value = 21
    rule.save()
    rule.reload()
    check("editing logic voids verification and deactivates",
          not rule.verified_by and not rule.active)

    err = raises(lambda: frappe.delete_doc("Deadline Rule", rule.name, force=1))
    check("deadline rule cannot be deleted", err is not None, err or "no error raised")

    frappe.db.rollback()
    print(f"\n{sum(results)}/{len(results)} checks passed")
