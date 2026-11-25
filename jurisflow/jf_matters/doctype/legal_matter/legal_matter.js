frappe.ui.form.on("Legal Matter", {
	refresh(frm) {
		if (frm.is_new()) return;
		frm.add_custom_button(
			__("Create Invoice"),
			() => {
				frappe.call({
					method: "jurisflow.services.billing_service.create_invoice_for_matter",
					args: { matter: frm.doc.name },
					freeze: true,
					callback: (r) =>
						r.message && frappe.set_route("Form", "Sales Invoice", r.message),
				});
			},
			__("Actions")
		);
		frm.add_custom_button(
			__("Log Time"),
			() => {
				frappe.new_doc("Legal Time Entry", {
					matter: frm.doc.name,
					advocate: frappe.session.user,
				});
			},
			__("Actions")
		);
		frm.add_custom_button(
			__("Add Hearing"),
			() => {
				frappe.new_doc("Court Hearing", { matter: frm.doc.name });
			},
			__("Actions")
		);
	},
});
