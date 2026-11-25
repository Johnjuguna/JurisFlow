from frappe import _


def get_data():
	return {
		"fieldname": "matter",
		"transactions": [
			{"label": _("Court"), "items": ["Court Hearing"]},
			{"label": _("Work"), "items": ["Matter Task", "Legal Time Entry"]},
		],
	}
