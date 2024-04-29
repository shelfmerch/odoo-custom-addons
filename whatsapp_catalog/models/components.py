from odoo import fields, models


class ComponentsInherit(models.Model):
    _inherit = "components"

    button_type = fields.Selection(selection_add=[("CATALOG", "Catalogue")])
    type_of_action = fields.Selection(
        selection_add=[("order_details", "Open Order Details")]
    )
    interactive_type = fields.Selection(
        selection_add=[
            ("order_details", "ORDER DETAILS"),
            ("catalog_message", "Catalog Message"),
        ]
    )
