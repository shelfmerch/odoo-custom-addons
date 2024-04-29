from odoo import _, api, fields, models, modules, tools
from odoo.exceptions import UserError
from odoo.addons.mail.models.discuss.discuss_channel_member import ChannelMember

class Channel(models.Model):
    _inherit = 'discuss.channel'

    whatsapp_channel = fields.Boolean(string="Whatsapp Channel")

    @api.constrains('channel_member_ids', 'channel_partner_ids')
    def _constraint_partners_chat(self):
        pass

@api.model_create_multi
def create(self, vals_list):
    if self.env.context.get("mail_create_bypass_create_check") is self._bypass_create_check:
        self = self.sudo()
    for vals in vals_list:
        if "channel_id" not in vals:
            raise UserError(
                _(
                    "It appears you're trying to create a channel member, but it seems like you forgot to specify the related channel. "
                    "To move forward, please make sure to provide the necessary channel information."
                )
            )
        channel = self.env["discuss.channel"].browse(vals["channel_id"])
    return super(ChannelMember, self).create(vals_list)

ChannelMember.create = create