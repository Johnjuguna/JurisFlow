"""Hook fragments for JF Deadlines, merged into hooks.py so hooks.py stays small and nothing is duplicated.
Pure Python (no frappe import) so it is unit-testable. Schedule comes from config/deadline_config.json."""

import json
import pathlib

_CFG = json.loads((pathlib.Path(__file__).parent / "config" / "deadline_config.json").read_text())
_MATTER_REFRESH = "jurisflow.services.matter_service.refresh_from_doc"
_JOB = "jurisflow.jobs.deadline_jobs.run_deadline_checks"


def merge_scheduler(existing):
	out = {**existing, "cron": {**existing.get("cron", {})}}
	jobs = out["cron"].setdefault(_CFG["check_cron"], [])
	if _JOB not in jobs:
		jobs.append(_JOB)
	return out


def merge_doc_events(existing):
	out = {k: dict(v) for k, v in existing.items()}
	out.setdefault("Computed Deadline", {}).setdefault("on_update", _MATTER_REFRESH)
	return out
