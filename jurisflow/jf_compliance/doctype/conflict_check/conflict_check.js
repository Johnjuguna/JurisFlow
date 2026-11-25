frappe.ui.form.on("Conflict Check", {
	refresh(frm) {
		if (frm.is_new()) return;

		const call = (method, args) =>
			frappe
				.call({
					method: "jurisflow.api.compliance." + method,
					args: Object.assign({ name: frm.doc.name }, args || {}),
					freeze: true,
				})
				.then(() => frm.reload_doc());

		const decide = (method) =>
			frappe.prompt(
				{ fieldname: "notes", fieldtype: "Small Text", label: __("Reason / Notes"), reqd: 1 },
				(v) => call(method, { notes: v.notes }),
				__("Partner decision")
			);

		const s = frm.doc.status;
		if (["Not Run", "Conflict Found"].includes(s)) {
			frm.add_custom_button(__("Run Conflict Search"), () => {
				if (frm.is_dirty()) return frappe.msgprint(__("Please save first."));
				call("run_conflict_search");
			});
		}
		if (s === "Conflict Found") {
			frm.add_custom_button(__("Clear Conflict"), () => decide("clear_conflict"), __("Partner"));
			frm.add_custom_button(__("Decline Instructions"), () => decide("decline_conflict"), __("Partner"));
		}
		if (["No Conflict", "Cleared by Partner"].includes(s) && !frm.doc.customer) {
			frm.add_custom_button(__("Create Customer"), () => call("create_customer"));
		}
	},
});
