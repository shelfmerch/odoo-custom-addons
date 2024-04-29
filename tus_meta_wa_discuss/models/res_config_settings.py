from ast import literal_eval

from odoo import api, fields, models,_


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    not_wa_msgs_btn_in_chatter = fields.Many2many("ir.model","send_wa_msgs_model_rel","model_id","send_wa_msgs_id")
    not_send_msgs_btn_in_chatter = fields.Many2many("ir.model","send_msgs_model_rel","model_id","send_msgs_id")

    def set_values(self):
        res = super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('tus_meta_wa_discuss.not_wa_msgs_btn_in_chatter', self.not_wa_msgs_btn_in_chatter.ids)
        self.env['ir.config_parameter'].sudo().set_param('tus_meta_wa_discuss.not_send_msgs_btn_in_chatter', self.not_send_msgs_btn_in_chatter.ids)
        return res

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()

        with_user = self.env['ir.config_parameter'].sudo()
        not_wa_msgs_btn_in_chatter = with_user.get_param('tus_meta_wa_discuss.not_wa_msgs_btn_in_chatter')
        not_send_msgs_btn_in_chatter = with_user.get_param('tus_meta_wa_discuss.not_send_msgs_btn_in_chatter')
        res.update(
            not_wa_msgs_btn_in_chatter=[(6, 0, literal_eval(not_wa_msgs_btn_in_chatter))] if not_wa_msgs_btn_in_chatter else False, )
        res.update(
            not_send_msgs_btn_in_chatter=[(6, 0, literal_eval(not_send_msgs_btn_in_chatter))] if not_send_msgs_btn_in_chatter else False, )
        return res