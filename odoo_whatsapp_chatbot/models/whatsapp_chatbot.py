# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.
from odoo import api, fields, models


class WhatsAppChatbot(models.Model):
    _name = "whatsapp.chatbot"
    _description = "Odoo Whatsapp Chatbot Automation"
    _rec_name = "title"
    _order = "title"

    title = fields.Char("Title", required=True, translate=True)
    active = fields.Boolean(default=True)
    image_1920 = fields.Image(readonly=False)
    step_type = fields.Selection(
        [
            ("message", "Message"),
            ("template", "Template"),
            ("interactive", "Interactive"),
        ],
        string="Step Type",
    )
    step_type_ids = fields.One2many(
        comodel_name="whatsapp.chatbot.script",
        inverse_name="whatsapp_chatbot_id",
        string="Message",
    )
    template_id = fields.Many2one(comodel_name="wa.template", string="WA Template")
    action_ids = fields.One2many(
        comodel_name="whatsapp.ir.actions", inverse_name="chatbot_id", string="Actions"
    )
    channel_ids = fields.One2many(
        comodel_name="discuss.channel", inverse_name="wa_chatbot_id", string="Channels"
    )
    wa_conversation_count = fields.Integer(
        "Number of conversation",
        compute="_compute_wa_conversation",
        store=False,
        readonly=True,
    )
    sequence = fields.Integer(string="Sequence")
    user_ids = fields.Many2many("res.users", string="Operators")

    @api.depends("channel_ids")
    def _compute_wa_conversation(self):
        data = self.env["discuss.channel"].read_group(
            [("wa_chatbot_id", "in", self._ids)],
            ["__count"],
            ["wa_chatbot_id"],
            lazy=False,
        )
        channel_count = {x["wa_chatbot_id"][0]: x["__count"] for x in data}
        for record in self:
            record.wa_conversation_count = channel_count.get(record.id, 0)
