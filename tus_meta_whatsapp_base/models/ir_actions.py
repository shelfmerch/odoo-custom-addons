import base64
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class BaseAutomation(models.Model):
    _inherit = 'base.automation'

    is_whatsapp_action = fields.Boolean(string='Is_whatsapp_action', required=False)

    @api.onchange('action_server_ids')
    def _onchange_get_whatsapp_actions(self):
        for val in self:
            val.is_whatsapp_action = bool(val.action_server_ids.filtered(lambda x: x.wa_template_id))


class ServerActions(models.Model):
    """ Add SMS option in server actions. """
    _name = 'ir.actions.server'
    _inherit = ['ir.actions.server']

    state = fields.Selection(selection_add=[
        ("whatsapp", "Send Whatsapp Message"),
    ], ondelete={"whatsapp": "cascade"})

    isWaMsgs = fields.Boolean(default=False)

    wa_template_id = fields.Many2one(
        'wa.template', 'WA Template', ondelete='set null',
        domain="[('model_id', '=', model_id)]",
    )

    def _run_action_whatsapp_multi(self, eval_context=None):
        # TDE CLEANME: when going to new api with server action, remove action
        if not self.wa_template_id or self._is_recompute():
            return False

        records = eval_context.get('records') or eval_context.get('record')
        if not records:
            return False

        for rec in records:
            if rec._name == 'res.partner':
                composer = self.env['wa.compose.message'].with_context(
                    default_model=rec._name,
                    default_res_id=rec.id,
                    default_template_id=self.wa_template_id.id,
                    default_partner_id=rec.id,
                ).create({})
                composer.send_whatsapp_message()
            elif rec._name == 'pos.order':
                report_id = self.env.ref('point_of_sale.pos_invoice_report').sudo()  # Action of the report
                pdf = report_id._render_qweb_pdf(rec.id)
                Attachment = self.env['ir.attachment'].sudo()
                b64_pdf = base64.b64encode(pdf[0])
                name = 'Invoice-%s.pdf' % rec.name
                # attac_id = Attachment.search([('name', '=', name)], limit=1)
                # if len(attac_id) == 0:
                attac_id = Attachment.create({'name': name,
                                              'type': 'binary',
                                              'datas': b64_pdf,
                                              'res_model': 'wa.msgs',
                                              })
                composer = self.env['wa.compose.message'].with_context(
                    default_model=rec._name,
                    default_res_id=rec.id,
                    default_template_id=self.wa_template_id.id,
                    default_partner_id=rec.partner_id.id,
                    default_attachment_ids=[(4, attac_id.id)],
                ).create({})
                composer.send_whatsapp_message()
            else:
                if rec.partner_id:
                    composer = self.env['wa.compose.message'].with_context(
                        default_model=rec._name,
                        default_res_id=rec.id,
                        default_template_id=self.wa_template_id.id,
                        default_partner_id=rec.partner_id.id,
                    ).create({})
                    composer.send_whatsapp_message()
        return False
