import json
import os

MODULE = "Jurisflow"
BASE = "apps/jurisflow/jurisflow/jurisflow/doctype"


def f(fieldname, label, fieldtype, **kw):
	d = {"fieldname": fieldname, "label": label, "fieldtype": fieldtype}
	d.update(kw)
	return d


PERMS_FULL = [
	{
		"role": "System Manager",
		"read": 1,
		"write": 1,
		"create": 1,
		"delete": 1,
		"report": 1,
		"export": 1,
		"print": 1,
		"email": 1,
		"share": 1,
	},
	{
		"role": "Legal Admin",
		"read": 1,
		"write": 1,
		"create": 1,
		"report": 1,
		"export": 1,
		"print": 1,
		"email": 1,
		"share": 1,
	},
	{"role": "Advocate", "read": 1, "write": 1, "create": 1, "report": 1, "print": 1, "email": 1, "share": 1},
]


def make(
	name,
	fields,
	istable=0,
	autoname=None,
	title_field=None,
	search_fields=None,
	perms=None,
	submittable=0,
	naming_rule=None,
):
	snake = name.lower().replace(" ", "_")
	path = os.path.join(BASE, snake)
	os.makedirs(path, exist_ok=True)
	doc = {
		"doctype": "DocType",
		"name": name,
		"module": MODULE,
		"custom": 0,
		"istable": istable,
		"editable_grid": 1 if istable else 0,
		"is_submittable": submittable,
		"engine": "InnoDB",
		"track_changes": 0 if istable else 1,
		"sort_field": "creation",
		"sort_order": "DESC",
		"fields": fields,
		"permissions": [] if istable else (perms or PERMS_FULL),
	}
	if autoname:
		doc["autoname"] = autoname
	if naming_rule:
		doc["naming_rule"] = naming_rule
	if title_field:
		doc["title_field"] = title_field
		doc["show_title_field_in_link"] = 1
	if search_fields:
		doc["search_fields"] = search_fields
	with open(os.path.join(path, f"{snake}.json"), "w") as fp:
		json.dump(doc, fp, indent=1)
	cls = name.replace(" ", "")
	py = os.path.join(path, f"{snake}.py")
	if not os.path.exists(py):
		with open(py, "w") as fp:
			fp.write(
				f"import frappe\nfrom frappe.model.document import Document\n\n\nclass {cls}(Document):\n    pass\n"
			)
	open(os.path.join(path, "__init__.py"), "a").close()
	print("created", name)


# ---------- Practice Area ----------
make(
	"Practice Area",
	[
		f("area_name", "Area Name", "Data", reqd=1, unique=1, in_list_view=1),
		f("default_hourly_rate", "Default Hourly Rate", "Currency", in_list_view=1),
		f("description", "Description", "Small Text"),
	],
	autoname="field:area_name",
)

# ---------- Matter Party (child) ----------
make(
	"Matter Party",
	[
		f("party_name", "Party Name", "Data", reqd=1, in_list_view=1),
		f(
			"role",
			"Role",
			"Select",
			options="Client\nOpposing Party\nOpposing Counsel\nWitness\nCo-Counsel\nOther",
			reqd=1,
			in_list_view=1,
		),
		f("id_number", "ID / Registration No.", "Data"),
		f("phone", "Phone", "Data", in_list_view=1),
		f("email", "Email", "Data", options="Email"),
	],
	istable=1,
)

# ---------- Legal Matter ----------
make(
	"Legal Matter",
	[
		f("title", "Matter Title", "Data", reqd=1, in_list_view=1),
		f("customer", "Client", "Link", options="Customer", reqd=1, in_list_view=1),
		f("practice_area", "Practice Area", "Link", options="Practice Area", reqd=1, in_standard_filter=1),
		f("column_break_1", "", "Column Break"),
		f(
			"status",
			"Status",
			"Select",
			options="Open\nOn Hold\nClosed\nArchived",
			default="Open",
			in_list_view=1,
			in_standard_filter=1,
		),
		f(
			"responsible_advocate",
			"Responsible Advocate",
			"Link",
			options="User",
			reqd=1,
			in_standard_filter=1,
		),
		f("opened_on", "Opened On", "Date", default="Today"),
		f("closed_on", "Closed On", "Date", read_only=1),
		f("section_court", "Court Details", "Section Break"),
		f("court", "Court / Tribunal", "Data"),
		f("case_no", "Case Number", "Data", in_list_view=1),
		f("opposing_party", "Opposing Party", "Data"),
		f("column_break_2", "", "Column Break"),
		f(
			"billing_type",
			"Billing Type",
			"Select",
			options="Hourly\nFixed Fee\nRetainer\nScale Fee",
			default="Hourly",
		),
		f("company", "Company", "Link", options="Company", default=None),
		f("section_parties", "Parties", "Section Break"),
		f("parties", "Parties", "Table", options="Matter Party"),
		f("section_billing", "Billing Summary", "Section Break"),
		f("unbilled_amount", "Unbilled Amount", "Currency", read_only=1),
		f("section_notes", "Notes", "Section Break"),
		f("description", "Description", "Text Editor"),
	],
	autoname="MAT-.YYYY.-.####",
	title_field="title",
	search_fields="title,customer,case_no",
)

# ---------- Court Hearing ----------
make(
	"Court Hearing",
	[
		f("matter", "Matter", "Link", options="Legal Matter", reqd=1, in_list_view=1, in_standard_filter=1),
		f("hearing_date", "Hearing Date", "Date", reqd=1, in_list_view=1, in_standard_filter=1),
		f("hearing_time", "Time", "Time"),
		f("column_break_1", "", "Column Break"),
		f("court", "Court", "Data", fetch_from="matter.court"),
		f(
			"purpose",
			"Purpose",
			"Select",
			options="Mention\nHearing\nPre-trial\nJudgment\nRuling\nMotion\nOther",
			in_list_view=1,
		),
		f(
			"status",
			"Status",
			"Select",
			options="Scheduled\nAttended\nAdjourned\nCancelled",
			default="Scheduled",
			in_list_view=1,
		),
		f("section_outcome", "Outcome", "Section Break"),
		f("outcome", "Outcome / Orders", "Text Editor"),
		f("next_date", "Next Date", "Date"),
	],
	autoname="HRG-.YYYY.-.#####",
)

# ---------- Matter Task ----------
make(
	"Matter Task",
	[
		f("matter", "Matter", "Link", options="Legal Matter", reqd=1, in_list_view=1),
		f("subject", "Subject", "Data", reqd=1, in_list_view=1),
		f("task_type", "Type", "Select", options="Task\nDeadline\nLimitation Date\nFiling"),
		f("column_break_1", "", "Column Break"),
		f("assigned_to", "Assigned To", "Link", options="User", in_list_view=1),
		f("due_date", "Due Date", "Date", reqd=1, in_list_view=1),
		f(
			"status",
			"Status",
			"Select",
			options="Open\nIn Progress\nDone\nCancelled",
			default="Open",
			in_list_view=1,
		),
		f("notes", "Notes", "Small Text"),
	],
	autoname="TSK-.YYYY.-.#####",
)

# ---------- Legal Time Entry ----------
make(
	"Legal Time Entry",
	[
		f("matter", "Matter", "Link", options="Legal Matter", reqd=1, in_list_view=1, in_standard_filter=1),
		f("customer", "Client", "Link", options="Customer", fetch_from="matter.customer", read_only=1),
		f("advocate", "Advocate", "Link", options="User", reqd=1, in_list_view=1),
		f("entry_date", "Date", "Date", reqd=1, default="Today", in_list_view=1),
		f("column_break_1", "", "Column Break"),
		f("hours", "Hours", "Float", reqd=1, in_list_view=1),
		f("rate", "Rate / Hour", "Currency", reqd=1),
		f("amount", "Amount", "Currency", read_only=1, in_list_view=1),
		f("billable", "Billable", "Check", default=1),
		f("billed", "Billed", "Check", read_only=1, in_standard_filter=1),
		f("invoice", "Sales Invoice", "Link", options="Sales Invoice", read_only=1),
		f("section_narr", "Narration", "Section Break"),
		f("narration", "Narration", "Small Text", reqd=1),
	],
	autoname="TIME-.YYYY.-.######",
	submittable=1,
)
