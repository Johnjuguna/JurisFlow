frappe.ui.form.on("Deadline Rule", {
  refresh(frm) {
    if (frm.is_new() || frm.doc.verified_by) return;
    frm.add_custom_button(__("Verify rule"), () => {
      frappe.confirm(__("I confirm this rule matches the statute cited and the counting convention is correct."), () => {
        frappe.call({
          method: "jurisflow.jf_deadlines.doctype.deadline_rule.deadline_rule.verify_rule",
          args: { name: frm.doc.name },
        }).then(() => frm.reload_doc());
      });
    });
  },
});
