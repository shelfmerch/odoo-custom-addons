# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.
from odoo import fields, models


class ChatbotMailChannel(models.Model):
    _inherit = "discuss.channel"

    wa_chatbot_id = fields.Many2one(
        comodel_name="whatsapp.chatbot", string="Whatsapp Chatbot"
    )
    message_ids = fields.One2many(
        "mail.message",
        "res_id",
        domain=lambda self: [
            ("wa_chatbot_id", "!=", False),
            ("wa_chatbot_id", "=", self.wa_chatbot_id.id),
        ],
        string="Messages",
    )
    script_sequence = fields.Integer(string="Sequence", default=1)
    is_chatbot_ended = fields.Boolean(string="Inactivate Chatbot")

    def chatbot_activate(self):
        channels = self.search([])
        for rec in channels:
            if rec.is_chatbot_ended:
                rec.is_chatbot_ended = False


class ChatbotMailMessage(models.Model):
    _inherit = "mail.message"

    wa_chatbot_id = fields.Many2one(
        comodel_name="whatsapp.chatbot", string="Whatsapp Chatbot"
    )
