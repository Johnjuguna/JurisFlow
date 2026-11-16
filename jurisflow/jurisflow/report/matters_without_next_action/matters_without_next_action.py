import frappe


def execute(filters=None):
    columns = [
        {"label": "Matter", "fieldname": "name", "fieldtype": "Link", "options": "Legal Matter", "width": 140},
        {"label": "Title", "fieldname": "title", "fieldtype": "Data", "width": 220},
        {"label": "Client", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 160},
        {"label": "Advocate", "fieldname": "responsible_advocate", "fieldtype": "Link", "options": "User", "width": 160},
        {"label": "Stage", "fieldname": "stage", "fieldtype": "Data", "width": 120},
        {"label": "Last Activity", "fieldname": "last_activity_on", "fieldtype": "Date", "width": 110},
        {"label": "Days Idle", "fieldname": "days_idle", "fieldtype": "Int", "width": 90},
    ]

    # Open matters with no future scheduled hearing and no open task due today or later.
    data = frappe.db.sql(
        """
        SELECT m.name, m.title, m.customer, m.responsible_advocate, m.stage, m.last_activity_on,
               DATEDIFF(CURDATE(), COALESCE(m.last_activity_on, DATE(m.creation))) AS days_idle
        FROM `tabLegal Matter` m
        WHERE m.status = 'Open'
          AND NOT EXISTS (
              SELECT 1 FROM `tabCourt Hearing` h
              WHERE h.matter = m.name AND h.status = 'Scheduled' AND h.hearing_date >= CURDATE())
          AND NOT EXISTS (
              SELECT 1 FROM `tabMatter Task` t
              WHERE t.matter = m.name AND t.status IN ('Open', 'In Progress') AND t.due_date >= CURDATE())
        ORDER BY days_idle DESC
        """,
        as_dict=True,
    )
    return columns, data
