# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    wa_chatbot_id = fields.Many2one(
        comodel_name="whatsapp.chatbot",
        related="company_id.wa_chatbot_id",
        string="Whatsapp Chatbot",
        readonly=False,
    )
