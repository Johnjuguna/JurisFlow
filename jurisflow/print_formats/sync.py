"""Keep app-shipped print formats in sync with the files in this folder.

Wired to the `after_migrate` hook, so `bench migrate` always converges the
database to what is in git. Safe to run repeatedly (only saves on change).
To add another format: drop a template next to this file and add one entry
to PRINT_FORMATS.
"""
from pathlib import Path

import frappe

TEMPLATE_DIR = Path(__file__).parent

PRINT_FORMATS = [
	{
		"name": "JurisFlow Fee Note",
		"doc_type": "Sales Invoice",
		"template": "fee_note.html",
	},
]

DEFAULTS = {
	"print_format_type": "Jinja",
	"custom_format": 1,
	"standard": "No",
	"disabled": 0,
	"print_format_builder": 0,
	"print_format_builder_beta": 0,
	"raw_printing": 0,
	"default_print_language": "en",
	"pdf_generator": "wkhtmltopdf",
	"font_size": 9,
	"margin_top": 10,
	"margin_bottom": 10,
	"margin_left": 10,
	"margin_right": 10,
	"css": "",
}


def sync():
	for spec in PRINT_FORMATS:
		html = (TEMPLATE_DIR / spec["template"]).read_text(encoding="utf-8")
		values = {**DEFAULTS, "doc_type": spec["doc_type"], "html": html}

		if frappe.db.exists("Print Format", spec["name"]):
			doc = frappe.get_doc("Print Format", spec["name"])
			if all(doc.get(k) == v for k, v in values.items()):
				continue
		else:
			doc = frappe.new_doc("Print Format")
			doc.name = spec["name"]

		doc.update(values)
		doc.flags.ignore_permissions = True
		doc.save()
		frappe.db.commit()
