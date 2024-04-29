from odoo import _, api, fields, models, modules, tools

class Thread(models.AbstractModel):
    _inherit = 'mail.thread'

    # def _notify_thread(self, message, msg_vals=False, **kwargs):
    #     if msg_vals.get('message_type') == 'wa_msgs':
    #         self = self._fallback_lang()

    #         msg_vals = msg_vals if msg_vals else {}
    #         recipients_data = self._notify_get_recipients(message, msg_vals, **kwargs)
    #         return []
    #     recipients_data = super()._notify_thread(message, msg_vals=msg_vals, **kwargs)
    #     return recipients_data


    def get_template_req_val(self, res_id, res_model):
        send_template_req = True
        record = self.env[res_model].browse(res_id)
        if res_model != 'discuss.channel':
            if res_model == 'res.partner':
                send_template_req = record.send_template_req
            else:
                if hasattr(self.env[res_model],'partner_id') and record.partner_id:
                    send_template_req = record.partner_id.send_template_req

        return send_template_req
