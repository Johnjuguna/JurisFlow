app_name = "jurisflow"
app_title = "JurisFlow"
app_publisher = "John Njuguna"
app_description = "Law firm practice management for ERPNext"
app_email = "kiangainjuguna@gmail.com"
app_license = "Proprietary"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "jurisflow",
# 		"logo": "/assets/jurisflow/logo.png",
# 		"title": "Law MAnagement system",
# 		"route": "/jurisflow",
# 		"has_permission": "jurisflow.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/jurisflow/css/jurisflow.css"
# app_include_js = "/assets/jurisflow/js/jurisflow.js"

# include js, css files in header of web template
# web_include_css = "/assets/jurisflow/css/jurisflow.css"
# web_include_js = "/assets/jurisflow/js/jurisflow.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "jurisflow/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "jurisflow/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "jurisflow.utils.jinja_methods",
# 	"filters": "jurisflow.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "jurisflow.install.before_install"
# after_install = "jurisflow.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "jurisflow.uninstall.before_uninstall"
# after_uninstall = "jurisflow.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "jurisflow.utils.before_app_install"
# after_app_install = "jurisflow.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "jurisflow.utils.before_app_uninstall"
# after_app_uninstall = "jurisflow.utils.after_app_uninstall"

# Build
# ------------------
# To hook into the build process

# after_build = "jurisflow.build.after_build"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "jurisflow.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"jurisflow.jobs.reminder_jobs.all"
# 	],
# 	"daily": [
# 		"jurisflow.jobs.reminder_jobs.daily"
# 	],
# 	"hourly": [
# 		"jurisflow.jobs.reminder_jobs.hourly"
# 	],
# 	"weekly": [
# 		"jurisflow.jobs.reminder_jobs.weekly"
# 	],
# 	"monthly": [
# 		"jurisflow.jobs.reminder_jobs.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "jurisflow.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "jurisflow.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "jurisflow.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "jurisflow.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["jurisflow.utils.before_request"]
# after_request = ["jurisflow.utils.after_request"]

# Job Events
# ----------
# before_job = ["jurisflow.utils.before_job"]
# after_job = ["jurisflow.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"jurisflow.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []

required_apps = ["frappe", "erpnext"]

after_install = "jurisflow.setup.install.after_install"

scheduler_events = {
    "daily": ["jurisflow.jobs.reminder_jobs.send_hearing_reminders"],
    "hourly": ["jurisflow.jobs.hearing_jobs.escalate_unconfirmed_hearings"],
    "cron": {"0 17 * * *": ["jurisflow.jobs.hearing_jobs.send_daily_court_brief"]},
}

_matter_refresh = "jurisflow.services.matter_service.refresh_from_doc"

doc_events = {
    "Legal Matter": {"validate": "jurisflow.services.conflict_service.enforce_gate"},
    "Matter Task": {"on_update": _matter_refresh, "after_delete": _matter_refresh},
    "Legal Time Entry": {
        "validate": "jurisflow.services.matter_service.time_entry_validate",
        "on_update": _matter_refresh,
        "after_delete": _matter_refresh,
    },
}


# --- JF Deadlines (managed block) ---
from jurisflow.deadline_hooks import merge_doc_events, merge_scheduler
scheduler_events = merge_scheduler(scheduler_events)
doc_events = merge_doc_events(doc_events)
