import base64

from odoo import _, fields, models, tools, api
from odoo.addons.payment import utils as payment_utils


class SaleOrderInherit(models.Model):
    _inherit = "sale.order"

    wa_message_id = fields.Char(string="Wa_message_id", required=False)
    is_whatsapp_so = fields.Boolean("WhatsApp SO")
    success_payment_transaction = fields.Char(
        string="Wa Payment Transaction", required=False
    )
    payment_link = fields.Char(string="Payment Link", compute="_generate_payment_link", store=True)

    def _send_commerce_manager(self):
        self.ensure_one()
        for res in self:
            if res and res.is_whatsapp_so:
                active_model = ""
                active_model_id = 0
                Attachment = self.env["ir.attachment"].sudo()
                template_state = res._context.get("template_state")
                catalogue_id = self.env["wa.catalogue"].search(
                    [("model_id", "=", self._name)]
                )
                send_template_id = self.env["wa.template"]
                if template_state == "send_payment":
                    send_template_id |= catalogue_id.payment_template
                    if catalogue_id.payment_type == 'odoopay':
                        Attachment |= self._get_attachment_catalog(model_id=res,
                                                                   report_name='sale.action_report_saleorder')

                if template_state == "success_payment":
                    send_template_id |= catalogue_id.success_template
                    res.action_confirm()
                    payment = (
                        res.env["sale.advance.payment.inv"]
                        .with_context(advance_payment_method="delivered")
                        .create({})
                    )
                    temp_data = (
                        payment.with_context(
                            active_ids=res.ids,
                            active_model="sale.order",
                            advance_payment_method="delivered",
                        )
                        .sudo()
                        .create_invoices()
                    )
                    invoice_id = res.invoice_ids.filtered(lambda x: x.state == "draft")
                    if invoice_id:
                        active_model_id += invoice_id.id
                        active_model += invoice_id._name
                        invoice_id.sudo().action_post()
                        Attachment |= self._get_attachment_catalog(model_id=invoice_id,report_name="account.account_invoices")

                if send_template_id:
                    channel = self.env["discuss.channel"]
                    provider_id = self._context.get("provider")
                    user_partner = provider_id.user_id.partner_id
                    channel |= res.partner_id.channel_provider_line_ids.filtered(
                        lambda x: x.provider_id == provider_id
                    ).channel_id
                    part_lst = []
                    part_lst.append(res.partner_id.id)
                    if user_partner and res.partner_id.id != user_partner.id:
                        part_lst.append(user_partner.id)
                    if not channel:
                        name = res.partner_id.mobile
                        channel |= self.env["discuss.channel"].create(
                            {
                                # 'public': 'public',
                                "channel_type": "chat",
                                "name": name,
                                "whatsapp_channel": True,
                                "channel_partner_ids": [(4, res.partner_id.id)],
                            }
                        )
                        channel.write(
                            {
                                "channel_member_ids": [(5, 0, 0)]
                                                      + [
                                                          (0, 0, {"partner_id": line_vals})
                                                          for line_vals in part_lst
                                                      ]
                            }
                        )
                        # Multi Companies and Multi Providers Code Here
                        # self.partner_id.write({'channel_provider_line_ids': [
                        #     (0, 0, {'channel_id': channel.id, 'provider_id': self.env.user.provider_id.id})]})
                        res.partner_id.write(
                            {
                                "channel_provider_line_ids": [
                                    (
                                        0,
                                        0,
                                        {
                                            "channel_id": channel.id,
                                            "provider_id": provider_id.id,
                                        },
                                    )
                                ]
                            }
                        )

                    wa_message_values = {}

                    if Attachment:
                        wa_message_values.update(
                            {
                                "attachment_ids": [
                                    (4, attac_id.id) for attac_id in Attachment
                                ]
                            }
                        )

                    if send_template_id.body_html != "":
                        wa_message_values.update(
                            {"body": tools.html2plaintext(send_template_id.body_html)}
                        )

                    wa_message_values.update(
                        {
                            "author_id": user_partner.id,
                            "email_from": user_partner.email or "",
                            "model": res._name,
                            "message_type": "wa_msgs",
                            "isWaMsgs": True,
                            "subtype_id": self.env["ir.model.data"]
                            .sudo()
                            ._xmlid_to_res_id("mail.mt_comment"),
                            "partner_ids": [(4, user_partner.id)],
                            "res_id": res.id,
                            "reply_to": user_partner.email,
                        }
                    )

                    wa_attach_message = (
                        self.env["mail.message"]
                        .sudo()
                        .with_user(provider_id.user_id.id)
                        .with_context(
                            {
                                "template_send": True,
                                "wa_template": send_template_id,
                                "active_model_id": active_model_id or res.id,
                                "active_model": active_model or res._name,
                                "provider_id": provider_id,
                                "attachment_ids": Attachment.ids,
                            }
                        )
                        .create(wa_message_values)
                    )

                    channel._notify_thread(wa_attach_message, wa_message_values)

    def _get_attachment_catalog(self, model_id, report_name):
        Attachment = self.env["ir.attachment"].sudo()
        name = ''
        if model_id._name == 'sale.order':
            name += ((model_id.state in ('draft', 'sent') and _('Quotation - %s') % model_id.name) or
                    _('Order - %s') % model_id.name)

            name += '%s.pdf' % name

        else:
            name += (
                           model_id.state in ("posted") and model_id.name
                   ) or _("Draft - %s") % model_id.name
            name += ".pdf"
        pdf = self.env['ir.actions.report']._render_qweb_pdf(report_name, model_id.id)

        b64_pdf = base64.b64encode(pdf[0])
        attac_id = Attachment.search([('name', '=', name)], limit=1)
        if len(attac_id) == 0:
            Attachment |= Attachment.create({'name': name,
                                             'type': 'binary',
                                             'datas': b64_pdf,
                                             'res_model': model_id._name if model_id else 'whatsapp.history',
                                             })
        return Attachment

    @api.depends('state', 'amount_total')
    def _generate_payment_link(self):
        for rec in self:
            if rec.state not in ['draft', 'cancel']:
                access_token = payment_utils.generate_access_token(
                    rec.partner_id.id, rec.amount_total, rec.currency_id.id
                )
                rec.payment_link = f'/payment/pay' \
                                   f'?reference={rec.name}' \
                                   f'&amount={rec.amount_total}' \
                                   f'&sale_order_id={rec.id}' \
                                   f'&access_token={access_token}'
