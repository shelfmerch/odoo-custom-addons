from odoo import models, api, fields, tools
import json
import requests
from odoo.exceptions import UserError, ValidationError

image_type = ['image/avif', 'image/bmp', 'image/gif', 'image/vnd.microsoft.icon', 'image/jpeg', 'image/png',
              'image/svg+xml', 'image/tiff', 'image/webp']
document_type = ['application/xhtml+xml', 'application/vnd.ms-excel',
                 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'application/xml',
                 'application/vnd.mozilla.xul+xml', 'application/zip',
                 'application/x-7z-compressed', 'application/x-abiword', 'application/x-freearc',
                 'application/vnd.amazon.ebook', 'application/octet-stream', 'application/x-bzip',
                 'application/x-bzip2', 'application/x-cdf', 'application/x-csh', 'application/msword',
                 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                 'application/vnd.ms-fontobject', 'application/epub+zip', 'application/gzip',
                 'application/java-archive', 'application/json', 'application/ld+json',
                 'application/vnd.apple.installer+xml', 'application/vnd.oasis.opendocument.presentation',
                 'application/vnd.oasis.opendocument.spreadsheet', 'application/vnd.oasis.opendocument.text',
                 'application/ogg', 'application/pdf', 'application/x-httpd-php', 'application/vnd.ms-powerpoint',
                 'application/vnd.openxmlformats-officedocument.presentationml.presentation', 'application/vnd.rar',
                 'application/rtf', 'application/x-sh', 'application/x-tar', 'application/vnd.visio']
audio_type = ['audio/aac', 'audio/midi', 'audio/x-midi', 'audio/mpeg', 'audio/ogg', 'audio/opus', 'audio/wav',
              'audio/webm', 'audio/3gpp', 'audio/3gpp2']
video_type = ['video/x-msvideo', 'video/mp4', 'video/mpeg', 'video/ogg', 'video/mp2t', 'video/webm', 'video/3gpp',
              'video/3gpp2']


class WhatsappHistory(models.Model):
    _description = 'Whatsapp History'
    _name = 'whatsapp.history'
    _rec_name = 'phone'

    provider_id = fields.Many2one('provider', 'Provider', readonly=True)
    author_id = fields.Many2one('res.partner', 'Author', readonly=True)
    partner_id = fields.Many2one('res.partner', 'Recipient', readonly=True)
    phone = fields.Char(string="Whatsapp Number", readonly=True)
    # phn_no = fields.Char('Phone Number')
    message = fields.Char('Message', readonly=True)
    type = fields.Selection([
        ('in queue', 'In queue'),
        ('sent', 'Sent'),
        ('delivered', 'delivered'),
        ('received', 'Received'), ('read', 'Read'), ('fail', 'Fail')], string='Type', default='in queue', readonly=True)
    attachment_ids = fields.Many2many(
        'ir.attachment', 'wa_history_attachment_rel',
        'wa_message_id', 'wa_attachment_id',
        string='Attachments', readonly=True)
    message_id = fields.Char("Message ID", readonly=True)
    fail_reason = fields.Char("Fail Reason", readonly=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, readonly=True)
    date = fields.Datetime('Date', default=fields.Datetime.now, readonly=True)
    model = fields.Char('Related Document Model', index=True, readonly=True)
    active = fields.Boolean('Active', default=True)
    rec_id = fields.Integer("Related Model ID", readonly=True)

    @api.onchange('partner_id')
    def _onchange_partner(self):
        # phone change to mobile
        for rec in self:
            self.phone = self.partner_id.mobile

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('is_interactive'):
                vals.pop('is_interactive')
                return super(WhatsappHistory, self).create(vals)
            if vals.get('is_chatbot'):
                vals.pop('is_chatbot')
                return super(WhatsappHistory, self).create(vals)
            if vals.get('is_commerce_manager', False):
                vals.pop('is_commerce_manager')
                return super(WhatsappHistory, self).create(vals)
            res = super(WhatsappHistory, self).create(vals)

            if res.provider_id and res.partner_id and res.partner_id.mobile:
                res.partner_id.write({'mobile': res.partner_id.mobile.strip('+').replace(' ', '')})
                part_lst = []
                part_lst.append(res.partner_id.id)
                if res.partner_id.id != vals.get('author_id'):
                    part_lst.append(int(vals.get('author_id')))
                channel = False
                operators = res.provider_id.mapped('user_ids')
                if res.type == 'received':
                    provider_channel_id = res.partner_id.channel_provider_line_ids.filtered(
                        lambda s: s.provider_id == res.provider_id)
                    if provider_channel_id:
                        channel = provider_channel_id.channel_id
                    else:
                        name = res.partner_id.name
                        channel = self.env['discuss.channel'].sudo().create({
                            # 'public': 'public',
                            'channel_type': 'chat',
                            'name': name,
                            'whatsapp_channel': True,
                            'channel_partner_ids': [(4, int(vals.get('partner_id'))), (4, int(vals.get('author_id')))],
                        })
                        mail_channel_partner = self.env['discuss.channel.member'].sudo().search(
                            [('channel_id', '=', channel.id),
                             ('partner_id', '=', int(vals.get('partner_id')))])
                        mail_channel_partner.write({'is_pinned': True})
                        channel.write({'channel_member_ids': [(5, 0, 0)] + [(0, 0, {'partner_id': line_vals}) for
                                                                            line_vals in part_lst]})

                        # channel.write({'channel_member_ids': [(5, 0, 0)] + [(0, 0, {'partner_id': line_vals}) for
                        # line_vals in part_lst]})
                        res.partner_id.write(
                            {'channel_provider_line_ids': [
                                (0, 0, {'channel_id': channel.id, 'provider_id': res.provider_id.id})]})

                    if channel:
                        message_values = {
                            'body': '<p> ' + res.message + '</p>',
                            'author_id': res.partner_id.id,
                            'email_from': res.partner_id.email or '',
                            'model': 'discuss.channel',
                            'message_type': 'wa_msgs',
                            'wa_message_id': vals.get('message_id'),
                            'isWaMsgs': True,
                            'subtype_id': self.env['ir.model.data'].sudo()._xmlid_to_res_id('mail.mt_comment'),
                            'partner_ids': [(4, res.partner_id.id)],
                            'res_id': channel.id,
                            'reply_to': res.partner_id.email,
                            'company_id': res.company_id.id,
                        }
                        if res.attachment_ids:
                            message_values.update({'attachment_ids': res.attachment_ids})
                        if 'quotedMsgId' in self.env.context:
                            parent_message = self.env['mail.message'].sudo().search_read(
                                [('wa_message_id', '=', self.env.context['quotedMsgId'])],
                                ['id', 'body', 'chatter_wa_model', 'chatter_wa_res_id', 'chatter_wa_message_id'])
                            if len(parent_message) > 0:
                                message_values.update({'parent_id': parent_message[0]['id']})
                                if parent_message[0].get('chatter_wa_model') and parent_message[0].get(
                                        'chatter_wa_res_id') and parent_message[0].get('chatter_wa_message_id'):
                                    chatter_wa_message_values = {
                                        'body': res.message or '',
                                        'author_id': res.partner_id.id,
                                        'email_from': res.partner_id.email or '',
                                        'model': parent_message[0].get('chatter_wa_model'),
                                        'message_type': 'comment',
                                        'isWaMsgs': True,
                                        'subtype_id': self.env['ir.model.data'].sudo()._xmlid_to_res_id(
                                            'mail.mt_comment'),
                                        # 'channel_ids': [(4, channel.id)],
                                        'partner_ids': [(4, res.partner_id.id)],
                                        'res_id': parent_message[0].get('chatter_wa_res_id'),
                                        'reply_to': res.partner_id.email,
                                        'parent_id': parent_message[0].get('chatter_wa_message_id'),
                                    }
                                    if vals.get('attachment_ids'):
                                        message_values.update({'attachment_ids': res.attachment_ids})
                                    chatter_wa_message = self.env['mail.message'].sudo().create(
                                        chatter_wa_message_values)
                                    # channel._notify_thread(chatter_wa_message, chatter_wa_message_values)
                                    # comment due to thread single message and message replace issue.
                                    # notifications = [(channel, 'discuss.channel/new_message',
                                    #                   {'id': channel.id, 'message': chatter_wa_message_values})]
                                    # self.env['bus.bus']._sendmany(notifications)

                        message = self.env['mail.message'].sudo().with_context({'message': 'received'}).create(
                            message_values)
                        channel._notify_thread(message, message_values)
                        # comment due to thread single message and message replace issue.
                        # notifications = [(channel, 'discuss.channel/new_message',
                        #                   {'id': channel.id, 'message': message_values})]
                        # self.env['bus.bus']._sendmany(notifications)

                    if operators:
                        for operator in operators:
                            operator_channel = operator.partner_id.channel_provider_line_ids.channel_id
                            if operator_channel:
                                if channel.whatsapp_channel:
                                    channel.sudo().write(
                                        {'channel_partner_ids': [(4, operator.partner_id.id)]})
                                    mail_channel_partner = self.env[
                                        'discuss.channel.member'].sudo().search(
                                        [('channel_id', '=', channel.id),
                                         ('partner_id', '=', operator.partner_id.id)])
                                    mail_channel_partner.write({'is_pinned': True})

                else:
                    if not self.env.context.get('whatsapp_application'):
                        if 'template_send' in self.env.context and self.env.context.get('template_send'):
                            wa_template = self.env.context.get('wa_template')
                            params = []

                            if wa_template.template_type == 'interactive':
                                for component in wa_template.components_ids:
                                    template_dict = {}
                                    if component.type == 'interactive':
                                        if component.interactive_type == 'product_list':
                                            if component.interactive_product_list_ids:
                                                section = []
                                                for product in component.interactive_product_list_ids:
                                                    product_items = []

                                                    for products in product.product_list_ids:
                                                        product_item = {
                                                            "product_retailer_id": products.product_retailer_id
                                                        }

                                                        product_items.append(product_item)

                                                    section.append({
                                                        "title": product.main_title,
                                                        "product_items": product_items
                                                    })

                                                action = {
                                                    "catalog_id": component.catalog_id,
                                                    "sections": section
                                                }

                                                template_dict.update(action)

                                        elif component.interactive_type == 'button':
                                            if component.interactive_button_ids:
                                                buttons = []
                                                for btn_id in component.interactive_button_ids:
                                                    buttons.append({
                                                        "type": "reply",
                                                        "reply": {
                                                            "id": btn_id.id,
                                                            "title": btn_id.title
                                                        }
                                                    })
                                                action = {
                                                    "buttons": buttons
                                                }

                                                template_dict.update(action)

                                        elif component.interactive_type == 'list':
                                            if component.interactive_list_ids:
                                                section = []
                                                for list_id in component.interactive_list_ids:
                                                    rows = []
                                                    for lists in list_id.title_ids:
                                                        title_ids = {
                                                            "id": lists.id,
                                                            "title": lists.title,
                                                            "description": lists.description or ''
                                                        }
                                                        rows.append(title_ids)

                                                    section.append({
                                                        'title': list_id.main_title,
                                                        'rows': rows
                                                    })
                                                action = {
                                                    "button": list_id.main_title,
                                                    "sections": section
                                                }
                                                template_dict.update(action)

                                        elif component.interactive_type == 'product':
                                            action = {
                                                "catalog_id": component.catalog_id,
                                                "product_retailer_id": component.product_retailer_id
                                            }
                                            template_dict.update(action)
                                        elif component.interactive_type == 'catalog_message':
                                            action = {
                                                'name': 'catalog_message',
                                                'parameters': {
                                                    "thumbnail_product_retailer_id": component.product_retailer_id},
                                            }
                                            template_dict.update(action)

                                    if bool(template_dict):
                                        params.append(template_dict)
                                answer = res.provider_id.send_mpm_template(wa_template.name, wa_template.lang.iso_code,
                                                                           wa_template.namespace, res.partner_id,
                                                                           params)
                                if answer.status_code == 200:
                                    dict = json.loads(answer.text)
                                    if res.provider_id.provider == 'graph_api':  # if condition for Graph API
                                        if 'messages' in dict and dict.get('messages') and dict.get('messages')[0].get(
                                                'id'):

                                            vals['message_id'] = dict.get('messages')[0].get('id')
                                            if self.env.context.get('wa_messsage_id'):
                                                self.env.context.get('wa_messsage_id').wa_message_id = \
                                                    dict.get('messages')[0].get('id')
                                    else:
                                        if 'sent' in dict and dict.get('sent'):
                                            message_id = dict['id']
                                            if self.env.context.get('wa_messsage_id'):
                                                self.env.context.get('wa_messsage_id').wa_message_id = dict['id']
                                        else:
                                            if not self.env.context.get('cron'):
                                                if 'message' in dict:
                                                    raise UserError(
                                                        (dict.get('message')))
                                                if 'error' in dict:
                                                    raise UserError(
                                                        (dict.get('error').get('message')))
                                            else:
                                                vals.update({'type': 'fail'})
                                                if 'error' in dict:
                                                    vals.update({'fail_reason': dict.get('error').get('message')})
                                return res

                            else:
                                for component in wa_template.components_ids:
                                    object_data = self.env[wa_template.model_id.model].search_read(
                                        [('id', '=', self.env.context.get('active_model_id'))])[0]

                                    template_dict = {}

                                    if component.type in ['body', 'footer']:
                                        if component.variables_ids:
                                            template_dict.update({'type': component.type})
                                            parameters = []
                                            for variable in component.variables_ids:
                                                parameter_dict = {}
                                                if variable.field_id.ttype == 'text':
                                                    if object_data.get(variable.field_id.name):
                                                        parameter_dict.update(
                                                            {'type': 'text',
                                                             'text': object_data.get(variable.field_id.name)})
                                                    else:
                                                        parameter_dict.update(
                                                            {'type': 'text',
                                                             'text': ''})
                                                if variable.field_id.ttype == 'many2one':
                                                    if object_data.get(variable.field_id.name):
                                                        parameter_dict.update(
                                                            {'type': 'text',
                                                             'text': object_data.get(variable.field_id.name)[1]})
                                                    else:
                                                        parameter_dict.update(
                                                            {'type': 'text',
                                                             'text': ''})
                                                if variable.field_id.ttype == 'integer':
                                                    parameter_dict.update(
                                                        {'type': 'text',
                                                         'text': str(object_data.get(variable.field_id.name))})
                                                if variable.field_id.ttype == 'float':
                                                    parameter_dict.update(
                                                        {'type': 'text',
                                                         'text': str(object_data.get(variable.field_id.name))})
                                                if variable.field_id.ttype == 'monetary':
                                                    currency_id = object_data.get('currency_id')[0]
                                                    currency = self.env['res.currency'].browse(currency_id)
                                                    text = False
                                                    if currency.position == 'after':
                                                        text = str(
                                                            object_data.get(variable.field_id.name)) + currency.symbol
                                                    else:
                                                        text = currency.symbol + str(
                                                            object_data.get(variable.field_id.name))
                                                    parameter_dict.update(
                                                        {'type': 'text', 'text': text})
                                                if variable.field_id.ttype in ['char', 'selection']:
                                                    if object_data.get(variable.field_id.name):
                                                        parameter_dict.update({'type': 'text', 'text': object_data.get(
                                                            variable.field_id.name)})
                                                    else:
                                                        parameter_dict.update(
                                                            {'type': 'text',
                                                             'text': ''})
                                                if variable.field_id.ttype == 'html':
                                                    if object_data.get(variable.field_id.name):
                                                        parameter_dict.update({'type': 'text',
                                                                               'text': tools.html2plaintext(
                                                                                   object_data.get(
                                                                                       variable.field_id.name))})
                                                    else:
                                                        parameter_dict.update(
                                                            {'type': 'text',
                                                             'text': ''})
                                                if variable.field_id.ttype in ["date"]:
                                                    if object_data.get(variable.field_id.name):
                                                        parameter_dict.update(
                                                            {
                                                                "type": "text",
                                                                "text": object_data.get(
                                                                    variable.field_id.name
                                                                ).strftime("%m/%d/%Y"),
                                                            }
                                                        )
                                                    else:
                                                        parameter_dict.update(
                                                            {"type": "text", "text": ""}
                                                        )
                                                if variable.field_id.ttype in ["datetime"]:
                                                    if object_data.get(variable.field_id.name):
                                                        parameter_dict.update(
                                                            {
                                                                "type": "text",
                                                                "text": object_data.get(
                                                                    variable.field_id.name
                                                                ).strftime("%m/%d/%Y"),
                                                            }
                                                        )
                                                    else:
                                                        parameter_dict.update(
                                                            {"type": "text", "text": ""}
                                                        )
                                                parameters.append(parameter_dict)
                                                template_dict.update({'parameters': parameters})

                                    if component.type == "header":
                                        if component.formate == "text":
                                            if component.variables_ids:
                                                template_dict.update(
                                                    {"type": component.type}
                                                )
                                                parameters = []
                                                for variable in component.variables_ids:
                                                    parameter_dict = {}
                                                    if (
                                                            variable.field_id.ttype
                                                            == "text"
                                                    ):
                                                        if object_data.get(
                                                                variable.field_id.name
                                                        ):
                                                            parameter_dict.update(
                                                                {
                                                                    "type": "text",
                                                                    "text": object_data.get(
                                                                        variable.field_id.name
                                                                    ),
                                                                }
                                                            )
                                                        else:
                                                            parameter_dict.update(
                                                                {
                                                                    "type": "text",
                                                                    "text": "",
                                                                }
                                                            )
                                                    if (
                                                            variable.field_id.ttype
                                                            == "many2one"
                                                    ):
                                                        if object_data.get(
                                                                variable.field_id.name
                                                        ):
                                                            parameter_dict.update(
                                                                {
                                                                    "type": "text",
                                                                    "text": object_data.get(
                                                                        variable.field_id.name
                                                                    )[
                                                                        1
                                                                    ],
                                                                }
                                                            )
                                                        else:
                                                            parameter_dict.update(
                                                                {
                                                                    "type": "text",
                                                                    "text": "",
                                                                }
                                                            )
                                                    if (
                                                            variable.field_id.ttype
                                                            == "integer"
                                                    ):
                                                        parameter_dict.update(
                                                            {
                                                                "type": "text",
                                                                "text": str(
                                                                    object_data.get(
                                                                        variable.field_id.name
                                                                    )
                                                                ),
                                                            }
                                                        )
                                                    if (
                                                            variable.field_id.ttype
                                                            == "float"
                                                    ):
                                                        parameter_dict.update(
                                                            {
                                                                "type": "text",
                                                                "text": str(
                                                                    object_data.get(
                                                                        variable.field_id.name
                                                                    )
                                                                ),
                                                            }
                                                        )
                                                    if (
                                                            variable.field_id.ttype
                                                            == "monetary"
                                                    ):
                                                        text = False
                                                        if currency.position == "after":
                                                            text = (
                                                                    str(
                                                                        object_data.get(
                                                                            variable.field_id.name
                                                                        )
                                                                    )
                                                                    + currency.symbol
                                                            )
                                                        else:
                                                            text = currency.symbol + str(
                                                                object_data.get(
                                                                    variable.field_id.name
                                                                )
                                                            )
                                                        parameter_dict.update(
                                                            {
                                                                "type": "text",
                                                                "text": text,
                                                            }
                                                        )
                                                    if variable.field_id.ttype in [
                                                        "char",
                                                        "selection",
                                                    ]:
                                                        if object_data.get(
                                                                variable.field_id.name
                                                        ):
                                                            parameter_dict.update(
                                                                {
                                                                    "type": "text",
                                                                    "text": object_data.get(
                                                                        variable.field_id.name
                                                                    ),
                                                                }
                                                            )
                                                        else:
                                                            parameter_dict.update(
                                                                {
                                                                    "type": "text",
                                                                    "text": "",
                                                                }
                                                            )
                                                    if variable.field_id.ttype == 'html':
                                                        if object_data.get(variable.field_id.name):
                                                            parameter_dict.update({'type': 'text',
                                                                                   'text': tools.html2plaintext(
                                                                                       object_data.get(
                                                                                           variable.field_id.name))})
                                                        else:
                                                            parameter_dict.update(
                                                                {'type': 'text',
                                                                 'text': ''})
                                                    if variable.field_id.ttype in ["date"]:
                                                        if object_data.get(variable.field_id.name):
                                                            parameter_dict.update(
                                                                {
                                                                    "type": "text",
                                                                    "text": object_data.get(
                                                                        variable.field_id.name
                                                                    ).strftime("%m/%d/%Y"),
                                                                }
                                                            )
                                                        else:
                                                            parameter_dict.update(
                                                                {"type": "text", "text": ""}
                                                            )
                                                    if variable.field_id.ttype in ["datetime"]:
                                                        if object_data.get(variable.field_id.name):
                                                            parameter_dict.update(
                                                                {
                                                                    "type": "text",
                                                                    "text": object_data.get(
                                                                        variable.field_id.name
                                                                    ).strftime("%m/%d/%Y"),
                                                                }
                                                            )
                                                        else:
                                                            parameter_dict.update(
                                                                {"type": "text", "text": ""}
                                                            )
                                                    parameters.append(parameter_dict)
                                                    template_dict.update(
                                                        {"parameters": parameters}
                                                    )

                                        if component.formate == "media":
                                            IrConfigParam = self.env[
                                                "ir.config_parameter"
                                            ].sudo()
                                            base_url = IrConfigParam.get_param(
                                                "web.base.url", False
                                            )
                                            if component.formate_media_type == 'dynamic':
                                                if component.media_type == "document":
                                                    if self.env.context.get(
                                                            "attachment_ids"
                                                    ):
                                                        template_dict.update(
                                                            {"type": component.type}
                                                        )
                                                        parameters = [
                                                            {
                                                                "type": component.media_type,
                                                                "document": {
                                                                    "link": base_url
                                                                            + "/web/content/"
                                                                            + str(
                                                                        self.env.context.get(
                                                                            "attachment_ids"
                                                                        )[
                                                                            0
                                                                        ]
                                                                    ),
                                                                    "filename": self.env[
                                                                        "ir.attachment"
                                                                    ]
                                                                    .sudo()
                                                                    .browse(
                                                                        self.env.context.get(
                                                                            "attachment_ids"
                                                                        )[
                                                                            0
                                                                        ]
                                                                    )
                                                                    .name,
                                                                },
                                                            }
                                                        ]
                                                        template_dict.update(
                                                            {"parameters": parameters}
                                                        )
                                                if component.media_type == "video":
                                                    if self.env.context.get(
                                                            "attachment_ids"
                                                    ):
                                                        template_dict.update(
                                                            {"type": component.type}
                                                        )
                                                        parameters = [
                                                            {
                                                                "type": component.media_type,
                                                                "video": {
                                                                    "link": base_url
                                                                            + "/web/content/"
                                                                            + str(
                                                                        self.env.context.get(
                                                                            "attachment_ids"
                                                                        )[
                                                                            0
                                                                        ]
                                                                    ),
                                                                },
                                                            }
                                                        ]
                                                        template_dict.update(
                                                            {"parameters": parameters}
                                                        )
                                                if component.media_type == "image":
                                                    if self.env.context.get(
                                                            "attachment_ids"
                                                    ):
                                                        template_dict.update(
                                                            {"type": component.type}
                                                        )
                                                        parameters = [
                                                            {
                                                                "type": component.media_type,
                                                                "image": {
                                                                    "link": base_url
                                                                            + "/web/image/ir.attachment/"
                                                                            + str(
                                                                        self.env.context.get(
                                                                            "attachment_ids"
                                                                        )[0]
                                                                    )
                                                                            + "/datas",
                                                                },
                                                            }
                                                        ]
                                                        template_dict.update(
                                                            {"parameters": parameters}
                                                        )

                                            elif component.formate_media_type == 'static':
                                                if component.media_type == "document":
                                                    if component.attachment_ids:
                                                        template_dict.update(
                                                            {"type": component.type}
                                                        )
                                                        parameters = [
                                                            {
                                                                "type": component.media_type,
                                                                "document": {
                                                                    "link": base_url
                                                                            + "/web/content/"
                                                                            + str(
                                                                        component.attachment_ids.ids[
                                                                            0
                                                                        ]
                                                                    ),
                                                                    "filename": self.env[
                                                                        "ir.attachment"
                                                                    ]
                                                                    .sudo()
                                                                    .browse(
                                                                        component.attachment_ids.ids[
                                                                            0
                                                                        ]
                                                                    )
                                                                    .name,
                                                                },
                                                            }
                                                        ]
                                                        template_dict.update(
                                                            {"parameters": parameters}
                                                        )
                                                if component.media_type == "video":
                                                    if component.attachment_ids:
                                                        template_dict.update(
                                                            {"type": component.type}
                                                        )
                                                        parameters = [
                                                            {
                                                                "type": component.media_type,
                                                                "video": {
                                                                    "link": base_url
                                                                            + "/web/content/"
                                                                            + str(
                                                                        component.attachment_ids.ids[
                                                                            0
                                                                        ]
                                                                    ),
                                                                },
                                                            }
                                                        ]
                                                        template_dict.update(
                                                            {"parameters": parameters}
                                                        )
                                                if component.media_type == "image":
                                                    if component.attachment_ids:
                                                        template_dict.update(
                                                            {"type": component.type}
                                                        )
                                                        parameters = [
                                                            {
                                                                "type": component.media_type,
                                                                "image": {
                                                                    "link": base_url
                                                                            + "/web/image/ir.attachment/"
                                                                            + str(
                                                                        component.attachment_ids.ids[0]
                                                                    )
                                                                            + "/datas",
                                                                },
                                                            }
                                                        ]
                                                        template_dict.update(
                                                            {"parameters": parameters}
                                                        )

                                    if component.type == "buttons":
                                        if component.button_type == 'call_to_action' and (
                                                component.type_of_action or component.type_of_action_2) == 'URL' and (
                                                component.url_type or component.url_type_2) == 'dynamic':
                                            compo = str(component.type)
                                            if component.variables_ids:
                                                template_dict.update(
                                                    {'type': compo.split('s')[0] if compo[-1] == 's' else compo,
                                                     'sub_type': component.type_of_action,
                                                     'index': 0, })
                                                if component.type_of_action_2:
                                                    template_dict.update(
                                                        {'type': compo.split('s')[0] if compo[-1] == 's' else compo,
                                                         'sub_type': component.type_of_action_2,
                                                         'index': 0, })
                                                parameters = []
                                                for variable in component.variables_ids:
                                                    parameter_dict = {}
                                                    if variable.field_id.ttype == 'text':
                                                        if object_data.get(variable.field_id.name):
                                                            parameter_dict.update(
                                                                {'type': 'text',
                                                                 'text': object_data.get(variable.field_id.name)})
                                                        else:
                                                            parameter_dict.update(
                                                                {'type': 'text',
                                                                 'text': ''})
                                                    if variable.field_id.ttype == 'many2one':
                                                        if object_data.get(variable.field_id.name):
                                                            parameter_dict.update(
                                                                {'type': 'text',
                                                                 'text': object_data.get(variable.field_id.name)[1]})
                                                        else:
                                                            parameter_dict.update(
                                                                {'type': 'text',
                                                                 'text': ''})
                                                    if variable.field_id.ttype == 'integer':
                                                        parameter_dict.update(
                                                            {'type': 'text',
                                                             'text': str(object_data.get(variable.field_id.name))})
                                                    if variable.field_id.ttype == 'float':
                                                        parameter_dict.update(
                                                            {'type': 'text',
                                                             'text': str(object_data.get(variable.field_id.name))})
                                                    if variable.field_id.ttype == 'monetary':
                                                        currency_id = object_data.get('currency_id')[0]
                                                        currency = self.env['res.currency'].browse(currency_id)
                                                        text = False
                                                        if currency.position == 'after':
                                                            text = str(
                                                                object_data.get(
                                                                    variable.field_id.name)) + currency.symbol
                                                        else:
                                                            text = currency.symbol + str(
                                                                object_data.get(variable.field_id.name))
                                                        parameter_dict.update(
                                                            {'type': 'text', 'text': text})
                                                    if variable.field_id.ttype in ['char', 'selection']:
                                                        if object_data.get(variable.field_id.name):
                                                            parameter_dict.update(
                                                                {'type': 'text', 'text': object_data.get(
                                                                    variable.field_id.name)})
                                                        else:
                                                            parameter_dict.update(
                                                                {'type': 'text',
                                                                 'text': ''})
                                                    if variable.field_id.ttype == 'html':
                                                        if object_data.get(variable.field_id.name):
                                                            parameter_dict.update({'type': 'text',
                                                                                   'text': tools.html2plaintext(
                                                                                       object_data.get(
                                                                                           variable.field_id.name))})
                                                        else:
                                                            parameter_dict.update(
                                                                {'type': 'text',
                                                                 'text': ''})
                                                    if variable.field_id.ttype in ["date"]:
                                                        if object_data.get(variable.field_id.name):
                                                            parameter_dict.update(
                                                                {
                                                                    "type": "text",
                                                                    "text": object_data.get(
                                                                        variable.field_id.name
                                                                    ).strftime("%m/%d/%Y"),
                                                                }
                                                            )
                                                        else:
                                                            parameter_dict.update(
                                                                {"type": "text", "text": ""}
                                                            )
                                                    if variable.field_id.ttype in ["datetime"]:
                                                        if object_data.get(variable.field_id.name):
                                                            parameter_dict.update(
                                                                {
                                                                    "type": "text",
                                                                    "text": object_data.get(
                                                                        variable.field_id.name
                                                                    ).strftime("%m/%d/%Y"),
                                                                }
                                                            )
                                                        else:
                                                            parameter_dict.update(
                                                                {"type": "text", "text": ""}
                                                            )
                                                    parameters.append(parameter_dict)
                                                    template_dict.update({'parameters': parameters})

                                        if component.button_type == "flow":
                                            compo = str(component.type)
                                            template_dict.update(
                                                {'type': compo.replace('s', ''),
                                                 'sub_type': 'flow',
                                                 'index': 0, "parameters": [{
                                                    "type": "action",
                                                    "action": {
                                                        "flow_token": component.flow_id,
                                                    }
                                                }]})
                                        if component.button_type == 'CATALOG':
                                            template_dict.update(
                                                {
                                                    "type": "button",
                                                    "sub_type": component.button_type,
                                                    "index": 0,
                                                    "parameters": [{
                                                        "type": "action",
                                                        "action": {
                                                            "thumbnail_product_retailer_id": component.product_retailer_id
                                                        }
                                                    }]
                                                })

                                    if bool(template_dict):
                                        params.append(template_dict)

                            answer = res.provider_id.send_template(wa_template.name, wa_template.lang.iso_code,
                                                                   wa_template.namespace, res.partner_id, params)
                            if answer.status_code == 200:
                                dict = json.loads(answer.text)
                                if res.provider_id.provider == 'graph_api':  # if condition for Graph API
                                    if 'messages' in dict and dict.get('messages') and dict.get('messages')[0].get(
                                            'id'):
                                        res.message_id = dict.get('messages')[0].get('id')
                                        if self.env.context.get('wa_messsage_id'):
                                            self.env.context.get('wa_messsage_id').wa_message_id = dict.get('messages')[
                                                0].get('id')
                                else:
                                    if 'sent' in dict and dict.get('sent'):
                                        res.message_id = dict['id']
                                        if self.env.context.get('wa_messsage_id'):
                                            self.env.context.get('wa_messsage_id').wa_message_id = dict['id']
                                    else:
                                        if not self.env.context.get('cron'):
                                            if 'message' in dict:
                                                raise UserError(
                                                    (dict.get('message')))
                                            if 'error' in dict:
                                                raise UserError(
                                                    (dict.get('error').get('message')))
                                        else:
                                            res.write({'type': 'fail'})
                                            if 'error' in dict:
                                                res.write({'fail_reason': dict.get('error').get('message')})

                        else:
                            if res.message:
                                answer = False
                                if 'message_parent_id' in self.env.context:
                                    parent_msg = self.env['mail.message'].sudo().search(
                                        [('id', '=', self.env.context.get('message_parent_id').id)])
                                    answer = res.provider_id.send_message(res.partner_id, res.message,
                                                                          parent_msg.wa_message_id)
                                else:
                                    answer = res.provider_id.send_message(res.partner_id, res.message)
                                if answer.status_code == 200:
                                    dict = json.loads(answer.text)
                                    if res.provider_id.provider == 'graph_api':  # if condition for Graph API
                                        if 'messages' in dict and dict.get('messages') and dict.get('messages')[0].get(
                                                'id'):
                                            res.message_id = dict.get('messages')[0].get('id')
                                            if self.env.context.get('wa_messsage_id'):
                                                self.env.context.get('wa_messsage_id').wa_message_id = \
                                                    dict.get('messages')[0].get('id')

                                    else:
                                        if 'sent' in dict and dict.get('sent'):
                                            res.message_id = dict['id']
                                            if self.env.context.get('wa_messsage_id'):
                                                self.env.context.get('wa_messsage_id').wa_message_id = dict['id']
                                        else:
                                            if not self.env.context.get('cron'):
                                                if 'message' in dict:
                                                    raise UserError(
                                                        (dict.get('message')))
                                                if 'error' in dict:
                                                    raise UserError(
                                                        (dict.get('error').get('message')))
                                            else:
                                                res.write({'type': 'fail'})
                                                if 'message' in dict:
                                                    res.write({'fail_reason': dict.get('message')})

                            if res.attachment_ids:
                                for attachment_id in res.attachment_ids:
                                    if res.provider_id.provider == 'chat_api':
                                        answer = res.provider_id.send_file(res.partner_id, attachment_id)
                                        if answer.status_code == 200:
                                            dict = json.loads(answer.text)
                                            if 'sent' in dict and dict.get('sent'):
                                                res.message_id = dict['id']
                                                if self.env.context.get('wa_messsage_id'):
                                                    self.env.context.get('wa_messsage_id').wa_message_id = dict['id']
                                            else:
                                                if not self.env.context.get('cron'):
                                                    if 'message' in dict:
                                                        raise UserError(
                                                            (dict.get('message')))
                                                    if 'error' in dict:
                                                        raise UserError(
                                                            (dict.get('error').get('message')))
                                                else:
                                                    res.write({'type': 'fail'})
                                                    if 'message' in dict:
                                                        res.write({'fail_reason': dict.get('message')})

                                    if res.provider_id.provider == 'graph_api':
                                        sent_type = False
                                        if attachment_id.mimetype in image_type:
                                            sent_type = 'image'
                                        elif attachment_id.mimetype in document_type:
                                            sent_type = 'document'
                                        elif attachment_id.mimetype in audio_type:
                                            sent_type = 'audio'
                                        elif attachment_id.mimetype in video_type:
                                            sent_type = 'video'
                                        else:
                                            sent_type = 'image'

                                        answer = res.provider_id.send_image(res.partner_id, attachment_id)
                                        if answer.status_code == 200:
                                            dict = json.loads(answer.text)
                                            media_id = dict.get('id')
                                            getimagebyid = res.provider_id.get_image_by_id(media_id, res.partner_id,
                                                                                           sent_type, attachment_id)
                                            if getimagebyid.status_code == 200:
                                                imagedict = json.loads(getimagebyid.text)
                                            if 'messages' in imagedict and imagedict.get('messages'):
                                                res.message_id = imagedict.get('id')
                                                if self.env.context.get('wa_messsage_id'):
                                                    self.env.context.get(
                                                        'wa_messsage_id').wa_message_id = imagedict.get('id')
                                            else:
                                                if not self.env.context.get('cron'):
                                                    if 'messages' in imagedict:
                                                        raise UserError(
                                                            (imagedict.get('message')))
                                                    if 'error' in imagedict:
                                                        raise UserError(
                                                            (imagedict.get('error').get('message')))
                                                else:
                                                    res.write({'type': 'fail'})
                                                    if 'messages' in imagedict:
                                                        res.write({'fail_reason': imagedict.get('message')})

                            # if operators:
                            #     for operator in operators:
                            #         if res.author_id != operator.partner_id:
                            #             channel = res.partner_id.channel_provider_line_ids.channel_id
                            #             if channel.whatsapp_channel:
                            #                 mail_channel_partner = self.env[
                            #                     'discuss.channel.member'].sudo().search(
                            #                     [('channel_id', '=', channel.id),
                            #                      ('partner_id', '=', operator.partner_id.id)])
                            #                 mail_channel_partner.write({'is_pinned': False})
                            #                 channel.sudo().write(
                            #                     {'channel_partner_ids': [(3, operator.partner_id.id)]})

            return res
