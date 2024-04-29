# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    wa_chatbot_id = fields.Many2one(
        comodel_name="whatsapp.chatbot", string="Whatsapp Chatbot"
    )
