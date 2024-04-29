from odoo import fields, models


class SaleOrderInherit(models.Model):
    _name = "wa.catalogue"
    _description = "WhatsApp Catalogue"
    _rec_name = "model_id"

    active = fields.Boolean("Active", default=True)
    catalogue_name = fields.Char("Catalogue Name")
    catalogue_id = fields.Char("Catalogue Id")
    payment_configuration_name = fields.Char("Payment Name")
    payment_template = fields.Many2one("wa.template", "Payment Template")
    success_template = fields.Many2one("wa.template", "Success Template")
    failed_template = fields.Many2one("wa.template", "Failed Template")
    model_id = fields.Many2one("ir.model", ondelete="cascade")
    company_id = fields.Many2one(
        "res.company",
        required=True,
        readonly=True,
        default=lambda self: self.env.company,
    )
    payment_type = fields.Selection(
        string="Payment type",
        selection=[
            ("upi", "UPI"),
            ("razorpay", "RazorPay"),
            ("payU", "pay U"),
            ("odoopay", "Odoo Payment method"),
        ],
        required=False,
    )
