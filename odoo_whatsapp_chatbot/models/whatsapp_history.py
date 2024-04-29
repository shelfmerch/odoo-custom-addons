# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.
import json

from odoo import api, fields, models, tools
from odoo.exceptions import UserError

image_type = [
    "image/avif",
    "image/bmp",
    "image/gif",
    "image/vnd.microsoft.icon",
    "image/jpeg",
    "image/png",
    "image/svg+xml",
    "image/tiff",
    "image/webp",
]
document_type = [
    "application/xhtml+xml",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/xml",
    "application/vnd.mozilla.xul+xml",
    "application/zip",
    "application/x-7z-compressed",
    "application/x-abiword",
    "application/x-freearc",
    "application/vnd.amazon.ebook",
    "application/octet-stream",
    "application/x-bzip",
    "application/x-bzip2",
    "application/x-cdf",
    "application/x-csh",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-fontobject",
    "application/epub+zip",
    "application/gzip",
    "application/java-archive",
    "application/json",
    "application/ld+json",
    "application/vnd.apple.installer+xml",
    "application/vnd.oasis.opendocument.presentation",
    "application/vnd.oasis.opendocument.spreadsheet",
    "application/vnd.oasis.opendocument.text",
    "application/ogg",
    "application/pdf",
    "application/x-httpd-php",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.rar",
    "application/rtf",
    "application/x-sh",
    "application/x-tar",
    "application/vnd.visio",
]
audio_type = [
    "audio/aac",
    "audio/midi",
    "audio/x-midi",
    "audio/mpeg",
    "audio/ogg",
    "audio/opus",
    "audio/wav",
    "audio/webm",
    "audio/3gpp",
    "audio/3gpp2",
]
video_type = [
    "video/x-msvideo",
    "video/mp4",
    "video/mpeg",
    "video/ogg",
    "video/mp2t",
    "video/webm",
    "video/3gpp",
    "video/3gpp2",
]


class WhatsappHistory(models.Model):
    _inherit = "whatsapp.history"

    channel_id = fields.Many2one(comodel_name="discuss.channel", string="Mail Channel")
    wa_chatbot_id = fields.Many2one(
        comodel_name="whatsapp.chatbot", string="Whatsapp Chatbot"
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('is_commerce_manager',False):
                return super(WhatsappHistory,self).create(vals)

            wa_template = self.env.context.get("wa_template")
            provider_id = self.env["provider"].browse(int(vals.get("provider_id", False)))
            partner_id = self.env["res.partner"].browse(int(vals.get("partner_id", False)))
            self.env.context.get("wa_message_id", False)
            channel = False
            user_partner = provider_id.user_id.partner_id
            res = True
            operators = provider_id.mapped('user_ids')
            if provider_id and partner_id and partner_id.mobile:
                partner_id.write({"mobile": partner_id.mobile.strip("+").replace(" ", "")})
                # partner = self.env['res.partner'].browse
                part_lst = []
                part_lst.append(partner_id.id)
                if partner_id.id != user_partner.id:
                    part_lst.append(user_partner.id)
                provider_channel_id = partner_id.channel_provider_line_ids.filtered(
                    lambda s: s.provider_id == provider_id
                )
                if provider_channel_id:
                    channel = provider_channel_id.channel_id

                if not channel:
                    name = partner_id.mobile
                    channel = (
                        self.env["discuss.channel"]
                        .sudo()
                        .create(
                            {
                                "channel_type": "chat",
                                "name": name,
                                "whatsapp_channel": True,
                                "channel_partner_ids": [
                                    (
                                        4,
                                        int(vals.get("partner_id"))
                                        if vals.get("partner_id")
                                        else False,
                                    ),
                                    (4, user_partner.id),
                                ],
                            }
                        )
                    )
                    mail_channel_partner = (
                        self.env["discuss.channel.member"]
                        .sudo()
                        .search(
                            [
                                ("channel_id", "=", channel.id),
                                ("partner_id", "=", user_partner.id),
                            ]
                        )
                    )
                    mail_channel_partner.write({"is_pinned": True})

                    channel.write(
                        {
                            "channel_member_ids": [(5, 0, 0)]
                                                  + [(0, 0, {"partner_id": line_vals}) for line_vals in part_lst]
                        }
                    )
                    partner_id.write(
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
                vals.update({"channel_id": channel.id})
                if not provider_id.company_id.wa_chatbot_id:
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

                if (
                        wa_template
                        and wa_template.template_type == "interactive"
                        and provider_id
                        and partner_id
                        and partner_id.mobile
                ):
                    if not self.env.context.get("whatsapp_application"):
                        if "template_send" in self.env.context and self.env.context.get(
                                "template_send"
                        ):
                            params = []
                            for component in wa_template.components_ids:
                                template_dict = {}
                                if component.type == "interactive":
                                    if component.interactive_type == "product_list":
                                        if component.interactive_product_list_ids:
                                            section = []
                                            for (
                                                    product
                                            ) in component.interactive_product_list_ids:
                                                product_items = []

                                                for products in product.product_list_ids:
                                                    product_item = {
                                                        "product_retailer_id": products.product_retailer_id
                                                    }

                                                    product_items.append(product_item)

                                                section.append(
                                                    {
                                                        "title": product.main_title,
                                                        "product_items": product_items,
                                                    }
                                                )

                                            action = {
                                                "catalog_id": component.catalog_id,
                                                "sections": section,
                                            }

                                            template_dict.update(action)

                                    elif component.interactive_type == "button":
                                        if component.interactive_button_ids:
                                            buttons = []
                                            for btn_id in component.interactive_button_ids:
                                                buttons.append(
                                                    {
                                                        "type": "reply",
                                                        "reply": {
                                                            "id": btn_id.id,
                                                            "title": btn_id.title,
                                                        },
                                                    }
                                                )
                                            action = {"buttons": buttons}

                                            template_dict.update(action)

                                    elif component.interactive_type == "list":
                                        if component.interactive_list_ids:
                                            section = []
                                            for list_id in component.interactive_list_ids:
                                                rows = []
                                                for lists in list_id.title_ids:
                                                    title_ids = {
                                                        "id": lists.id,
                                                        "title": lists.title,
                                                        "description": lists.description
                                                                       or "",
                                                    }
                                                    rows.append(title_ids)

                                                section.append(
                                                    {
                                                        "title": list_id.main_title,
                                                        "rows": rows,
                                                    }
                                                )
                                            action = {
                                                "button": list_id.main_title,
                                                "sections": section,
                                            }
                                            template_dict.update(action)

                                    elif component.interactive_type == "product":
                                        action = {
                                            "catalog_id": component.catalog_id,
                                            "product_retailer_id": component.product_retailer_id,
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

                            if wa_template.template_type == "interactive":
                                answer = provider_id.send_mpm_template(
                                    wa_template.name,
                                    wa_template.lang.iso_code,
                                    wa_template.namespace,
                                    partner_id,
                                    params,
                                )
                                if answer.status_code == 200:
                                    dict = json.loads(answer.text)
                                    if (
                                            provider_id.provider == "graph_api"
                                    ):  # if condition for Graph API
                                        if (
                                                "messages" in dict
                                                and dict.get("messages")
                                                and dict.get("messages")[0].get("id")
                                        ):

                                            vals["message_id"] = dict.get("messages")[
                                                0
                                            ].get("id")
                                            if self.env.context.get("wa_messsage_id"):
                                                self.env.context.get(
                                                    "wa_messsage_id"
                                                ).wa_message_id = dict.get("messages")[
                                                    0
                                                ].get(
                                                    "id"
                                                )
                                    else:
                                        if "sent" in dict and dict.get("sent"):
                                            dict["id"]
                                            if self.env.context.get("wa_messsage_id"):
                                                self.env.context.get(
                                                    "wa_messsage_id"
                                                ).wa_message_id = dict["id"]
                                        else:
                                            if not self.env.context.get("cron"):
                                                if "message" in dict:
                                                    raise UserError(dict.get("message"))
                                                if "error" in dict:
                                                    raise UserError(
                                                        dict.get("error").get("message")
                                                    )
                                            else:
                                                vals.update({"type": "fail"})
                                                if "error" in dict:
                                                    vals.update(
                                                        {
                                                            "fail_reason": dict.get(
                                                                "error"
                                                            ).get("message")
                                                        }
                                                    )
                            vals.update({"is_interactive": True})
                            res = super(WhatsappHistory, self).create(vals)
                            return res

                else:
                    user_partner = provider_id.user_id.partner_id
                    if provider_id and partner_id and partner_id.mobile:
                        partner_id.write(
                            {"mobile": partner_id.mobile.strip("+").replace(" ", "")}
                        )
                        # partner = self.env['res.partner'].browse
                        part_lst = []
                        part_lst.append(partner_id.id)
                        part_lst.append(user_partner.id)

                        if vals.get("type") == "received":
                            message_script = (
                                self.env["whatsapp.chatbot"]
                                .search([])
                                .mapped("step_type_ids")
                                .filtered(lambda l: l.message == vals.get("message"))
                            )
                            chatbot_script_lines = message_script
                            if channel:
                                message_values = {
                                    "body": "<p> " + vals.get("message") + "</p>",
                                    "author_id": partner_id.id,
                                    "email_from": partner_id.email or "",
                                    "model": "discuss.channel",
                                    "message_type": "wa_msgs",
                                    "wa_message_id": vals.get("message_id"),
                                    "isWaMsgs": True,
                                    "subtype_id": self.env["ir.model.data"]
                                    .sudo()
                                    ._xmlid_to_res_id("mail.mt_comment"),
                                    "partner_ids": [(4, partner_id.id)],
                                    "res_id": channel.id,
                                    "reply_to": partner_id.email,
                                    "company_id": vals.get("company_id"),
                                }
                                if chatbot_script_lines:
                                    for chat in chatbot_script_lines:
                                        message_values.update(
                                            {"wa_chatbot_id": chat.whatsapp_chatbot_id.id}
                                        )
                                if vals.get("attachment_ids"):
                                    message_values.update(
                                        {"attachment_ids": vals.get("attachment_ids")}
                                    )
                                if "quotedMsgId" in self.env.context:
                                    parent_message = (
                                        self.env["mail.message"]
                                        .sudo()
                                        .search_read(
                                            [
                                                (
                                                    "wa_message_id",
                                                    "=",
                                                    self.env.context["quotedMsgId"],
                                                )
                                            ],
                                            [
                                                "id",
                                                "body",
                                                "chatter_wa_model",
                                                "chatter_wa_res_id",
                                                "chatter_wa_message_id",
                                            ],
                                        )
                                    )
                                    if len(parent_message) > 0:
                                        message_values.update(
                                            {"parent_id": parent_message[0]["id"]}
                                        )
                                        if (
                                                parent_message[0].get("chatter_wa_model")
                                                and parent_message[0].get("chatter_wa_res_id")
                                                and parent_message[0].get(
                                            "chatter_wa_message_id"
                                        )
                                        ):
                                            chatter_wa_message_values = {
                                                "body": vals.get("message"),
                                                "author_id": partner_id.id,
                                                "email_from": partner_id.email or "",
                                                "model": parent_message[0].get(
                                                    "chatter_wa_model"
                                                ),
                                                "message_type": "comment",
                                                "isWaMsgs": True,
                                                "subtype_id": self.env["ir.model.data"]
                                                .sudo()
                                                ._xmlid_to_res_id("mail.mt_comment"),
                                                "partner_ids": [(4, partner_id.id)],
                                                "res_id": parent_message[0].get(
                                                    "chatter_wa_res_id"
                                                ),
                                                "reply_to": partner_id.email,
                                                "parent_id": parent_message[0].get(
                                                    "chatter_wa_message_id"
                                                ),
                                            }
                                            if chatbot_script_lines:
                                                for chat in chatbot_script_lines:
                                                    message_values.update(
                                                        {
                                                            "wa_chatbot_id": chat.whatsapp_chatbot_id.id
                                                        }
                                                    )
                                            if vals.get("attachment_ids"):
                                                message_values.update(
                                                    {
                                                        "attachment_ids": vals.get(
                                                            "attachment_ids"
                                                        )
                                                    }
                                                )
                                            chatter_wa_message = (
                                                self.env["mail.message"]
                                                .sudo()
                                                .create(chatter_wa_message_values)
                                            )
                                            channel._notify_thread(chatter_wa_message, chatter_wa_message_values)
                                            # comment due to thread single message and message replace issue.
                                            # notifications = [(channel, 'discuss.channel/new_message',
                                            #                   {'id': channel.id, 'message': chatter_wa_message_values})]
                                            # self.env["bus.bus"]._sendmany(notifications)

                                message = (self.env["mail.message"].sudo().with_context({"message": "received"}).create(message_values))

                                channel._notify_thread(message, message_values)
                                # comment due to thread single message and message replace issue.

                                # message_values['temp_msg_id'] = message.id
                                # message_values['temporary_id'] = message.id + 0.01
                                # notifications = [(channel, 'discuss.channel/new_message',
                                #                   {'id': channel.id, 'message': message_values})]
                                # self.env["bus.bus"]._sendmany(notifications)
                        else:
                            if not self.env.context.get("whatsapp_application"):
                                if (
                                        "template_send" in self.env.context
                                        and self.env.context.get("template_send")
                                ):
                                    wa_template = self.env.context.get("wa_template")
                                    params = []

                                    active_model_id = self.env.context.get(
                                        "active_model_id"
                                    )
                                    if "active_model_id_chat_bot" in self.env.context:
                                        active_model_id = self.env.context.get(
                                            "active_model_id_chat_bot"
                                        )

                                    for component in wa_template.components_ids:
                                        object_data = self.env[
                                            wa_template.model_id.model
                                        ].search_read([("id", "=", active_model_id)])

                                        if object_data:
                                            object_data = object_data[0]

                                        template_dict = {}

                                        if component.type in ["body", "footer"]:
                                            if component.variables_ids:
                                                template_dict.update(
                                                    {"type": component.type}
                                                )
                                                parameters = []
                                                for variable in component.variables_ids:
                                                    parameter_dict = {}
                                                    if variable.field_id.ttype == "text":
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
                                                                {"type": "text", "text": ""}
                                                            )
                                                    if (
                                                            variable.field_id.ttype
                                                            == "many2many"
                                                    ):
                                                        parameter_dict.update(
                                                            {
                                                                "type": "text",
                                                                "text": partner_id.name,
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
                                                                    )[1],
                                                                }
                                                            )
                                                        else:
                                                            parameter_dict.update(
                                                                {"type": "text", "text": ""}
                                                            )
                                                    if variable.field_id.ttype == "integer":
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
                                                    if variable.field_id.ttype == "float":
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
                                                        if "currency_id" in object_data:
                                                            currency_id = object_data.get(
                                                                "currency_id"
                                                            )[0]
                                                            currency = self.env[
                                                                "res.currency"
                                                            ].browse(currency_id)
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
                                                                    round(object_data.get(variable.field_id.name), 2)
                                                                )
                                                        parameter_dict.update(
                                                            {"type": "text", "text": text}
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
                                                                {"type": "text", "text": ""}
                                                            )
                                                    if variable.field_id.ttype in ["date"]:
                                                        if object_data.get(
                                                                variable.field_id.name
                                                        ):
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
                                                    if variable.field_id.ttype in [
                                                        "datetime"
                                                    ]:
                                                        if object_data.get(
                                                                variable.field_id.name
                                                        ):
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
                                                    parameters.append(parameter_dict)
                                                template_dict.update(
                                                    {"parameters": parameters}
                                                )

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
                                                        if variable.field_id.ttype in ["date"]:
                                                            if object_data.get(
                                                                    variable.field_id.name
                                                            ):
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
                                                            if object_data.get(
                                                                    variable.field_id.name
                                                            ):
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
                                                                     'text': object_data.get(variable.field_id.name)[
                                                                         1]})
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
                                                        parameters.append(parameter_dict)
                                                        template_dict.update({'parameters': parameters})

                                            if component.button_type == "flow":
                                                compo = str(component.type)
                                                template_dict.update(
                                                    {'type': compo.replace('s', ''),
                                                     'sub_type': 'flow',
                                                     'index': 0, "parameters":[{
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
                                                        "parameters": [
                                                            {
                                                                "type": "action",
                                                                "action": {
                                                                    "thumbnail_product_retailer_id": component.product_retailer_id
                                                                }
                                                            }]
                                                    })
                                        if bool(template_dict):
                                            params.append(template_dict)
                                    answer = provider_id.send_template(
                                        wa_template.name,
                                        wa_template.lang.iso_code,
                                        wa_template.namespace,
                                        partner_id,
                                        params,
                                    )
                                    if answer.status_code == 200:
                                        dict = json.loads(answer.text)
                                        if (
                                                provider_id.provider == "graph_api"
                                        ):  # if condition for Graph API
                                            if (
                                                    "messages" in dict
                                                    and dict.get("messages")
                                                    and dict.get("messages")[0].get("id")
                                            ):
                                                vals["message_id"] = dict.get("messages")[
                                                    0
                                                ].get("id")

                                                if self.env.context.get("wa_messsage_id"):
                                                    self.env.context.get(
                                                        "wa_messsage_id"
                                                    ).wa_message_id = dict.get("messages")[
                                                        0
                                                    ].get(
                                                        "id"
                                                    )
                                        else:
                                            if "sent" in dict and dict.get("sent"):
                                                vals["message_id"] = dict["id"]
                                                if self.env.context.get("wa_messsage_id"):
                                                    self.env.context.get(
                                                        "wa_messsage_id"
                                                    ).wa_message_id = dict["id"]
                                            else:
                                                if not self.env.context.get("cron"):
                                                    if "message" in dict:
                                                        raise UserError(
                                                            dict.get("message")
                                                        )
                                                    if "error" in dict:
                                                        raise UserError(
                                                            dict.get("error").get(
                                                                "message"
                                                            )
                                                        )
                                                else:
                                                    vals.update({"type": "fail"})
                                                    if "error" in dict:
                                                        vals.update(
                                                            {
                                                                "fail_reason": dict.get(
                                                                    "error"
                                                                ).get("message")
                                                            }
                                                        )

                                else:
                                    if vals.get("message"):
                                        answer = False
                                        if "message_parent_id" in self.env.context:
                                            parent_msg = (
                                                self.env["mail.message"]
                                                .sudo()
                                                .search(
                                                    [
                                                        (
                                                            "id",
                                                            "=",
                                                            self.env.context.get(
                                                                "message_parent_id"
                                                            ).id,
                                                        )
                                                    ]
                                                )
                                            )
                                            answer = provider_id.send_message(
                                                partner_id,
                                                vals.get("message"),
                                                parent_msg.wa_message_id,
                                            )
                                        else:
                                            answer = provider_id.send_message(
                                                partner_id, vals.get("message")
                                            )
                                        if answer.status_code == 200:
                                            dict = json.loads(answer.text)
                                            if (
                                                    provider_id.provider == "graph_api"
                                            ):  # if condition for Graph API
                                                if (
                                                        "messages" in dict
                                                        and dict.get("messages")
                                                        and dict.get("messages")[0].get("id")
                                                ):
                                                    vals["message_id"] = dict.get(
                                                        "messages"
                                                    )[0].get("id")
                                                    if self.env.context.get(
                                                            "wa_messsage_id"
                                                    ):
                                                        self.env.context.get(
                                                            "wa_messsage_id"
                                                        ).wa_message_id = dict.get(
                                                            "messages"
                                                        )[
                                                            0
                                                        ].get(
                                                            "id"
                                                        )

                                            else:
                                                if "sent" in dict and dict.get("sent"):
                                                    vals["message_id"] = dict["id"]
                                                    if self.env.context.get(
                                                            "wa_messsage_id"
                                                    ):
                                                        self.env.context.get(
                                                            "wa_messsage_id"
                                                        ).wa_message_id = dict["id"]
                                                else:
                                                    if not self.env.context.get("cron"):
                                                        if "message" in dict:
                                                            raise UserError(
                                                                dict.get("message")
                                                            )
                                                        if "error" in dict:
                                                            raise UserError(
                                                                dict.get("error").get(
                                                                    "message"
                                                                )
                                                            )
                                                    else:
                                                        vals.update({"type": "fail"})
                                                        if "message" in dict:
                                                            vals.update(
                                                                {
                                                                    "fail_reason": dict.get(
                                                                        "message"
                                                                    )
                                                                }
                                                            )

                                    if vals.get("attachment_ids"):
                                        for attachment in vals.get("attachment_ids"):
                                            if attachment[1]:
                                                attachment_id = (
                                                    self.env["ir.attachment"]
                                                    .sudo()
                                                    .browse(attachment[1])
                                                )

                                                if provider_id.provider == "chat_api":
                                                    answer = provider_id.send_file(
                                                        partner_id, attachment_id
                                                    )
                                                    if answer.status_code == 200:
                                                        dict = json.loads(answer.text)
                                                        if "sent" in dict and dict.get(
                                                                "sent"
                                                        ):
                                                            vals["message_id"] = dict["id"]
                                                            if self.env.context.get(
                                                                    "wa_messsage_id"
                                                            ):
                                                                self.env.context.get(
                                                                    "wa_messsage_id"
                                                                ).wa_message_id = dict["id"]
                                                        else:
                                                            if not self.env.context.get(
                                                                    "cron"
                                                            ):
                                                                if "message" in dict:
                                                                    raise UserError(
                                                                        dict.get(
                                                                            "message"
                                                                        )
                                                                    )
                                                                if "error" in dict:
                                                                    raise UserError(
                                                                        dict.get(
                                                                            "error"
                                                                        ).get("message")
                                                                    )
                                                            else:
                                                                vals.update(
                                                                    {"type": "fail"}
                                                                )
                                                                if "message" in dict:
                                                                    vals.update(
                                                                        {
                                                                            "fail_reason": dict.get(
                                                                                "message"
                                                                            )
                                                                        }
                                                                    )

                                                if provider_id.provider == "graph_api":
                                                    sent_type = False
                                                    if attachment_id.mimetype in image_type:
                                                        sent_type = "image"
                                                    elif (
                                                            attachment_id.mimetype
                                                            in document_type
                                                    ):
                                                        sent_type = "document"
                                                    elif (
                                                            attachment_id.mimetype in audio_type
                                                    ):
                                                        sent_type = "audio"
                                                    elif (
                                                            attachment_id.mimetype in video_type
                                                    ):
                                                        sent_type = "video"
                                                    else:
                                                        sent_type = "image"

                                                    answer = provider_id.send_image(
                                                        partner_id, attachment_id
                                                    )
                                                    if answer.status_code == 200:
                                                        dict = json.loads(answer.text)
                                                        media_id = dict.get("id")
                                                        getimagebyid = (
                                                            provider_id.get_image_by_id(
                                                                media_id,
                                                                partner_id,
                                                                sent_type,
                                                                attachment_id,
                                                            )
                                                        )
                                                        if getimagebyid.status_code == 200:
                                                            imagedict = json.loads(
                                                                getimagebyid.text
                                                            )
                                                        if (
                                                                "messages" in imagedict
                                                                and imagedict.get("messages")
                                                        ):
                                                            vals[
                                                                "message_id"
                                                            ] = imagedict.get("id")
                                                            if self.env.context.get(
                                                                    "wa_messsage_id"
                                                            ):
                                                                self.env.context.get(
                                                                    "wa_messsage_id"
                                                                ).wa_message_id = imagedict.get(
                                                                    "id"
                                                                )
                                                        else:
                                                            if not self.env.context.get(
                                                                    "cron"
                                                            ):
                                                                if "messages" in imagedict:
                                                                    raise UserError(
                                                                        imagedict.get(
                                                                            "message"
                                                                        )
                                                                    )
                                                                if "error" in imagedict:
                                                                    raise UserError(
                                                                        imagedict.get(
                                                                            "error"
                                                                        ).get("message")
                                                                    )
                                                            else:
                                                                vals.update(
                                                                    {"type": "fail"}
                                                                )
                                                                if "messages" in imagedict:
                                                                    vals.update(
                                                                        {
                                                                            "fail_reason": imagedict.get(
                                                                                "message"
                                                                            )
                                                                        }
                                                                    )

                    vals.update({"is_chatbot": True})

                    res = super(WhatsappHistory, self).create(vals)

                    if vals.get("message") and vals.get("type") == "received":

                        if provider_id.company_id and provider_id.company_id.wa_chatbot_id:
                            # Bot
                            # if provider_id.company_id.wa_chatbot_id.mapped(
                            #         "step_type_ids"
                            # ).filtered(lambda l: l.message == vals.get("message")):
                            #     channel.sudo().write(
                            #         {
                            #             "wa_chatbot_id": provider_id.company_id.wa_chatbot_id.id
                            #             if provider_id.company_id
                            #                and provider_id.company_id.wa_chatbot_id
                            #             else False,
                            #         }
                            #     )

                            if (provider_id.company_id.wa_chatbot_id
                                    and not channel.is_chatbot_ended):
                                message_script = (
                                    self.env["whatsapp.chatbot"]
                                    .search([("id", "=", provider_id.company_id.wa_chatbot_id.id)])
                                    .mapped("step_type_ids")
                                    .filtered(lambda l: l.message == vals.get("message"))
                                )
                                current__chat_seq_script = (
                                    self.env["whatsapp.chatbot"]
                                    .search([("id", "=", provider_id.company_id.wa_chatbot_id.id)])
                                    .mapped("step_type_ids")
                                    .filtered(
                                        lambda l: l.sequence == channel.script_sequence
                                    )
                                )

                                chatbot_script_lines = message_script

                                if not chatbot_script_lines and provider_id.company_id.wa_chatbot_id.step_type_ids:
                                    chatbot_script_lines = provider_id.company_id.wa_chatbot_id.step_type_ids[0]

                                for chat in chatbot_script_lines:
                                    if chat.sequence >= channel.script_sequence:
                                        channel.write(
                                            {
                                                "wa_chatbot_id": chat.whatsapp_chatbot_id.id if provider_id.company_id and provider_id.company_id.wa_chatbot_id == chat.whatsapp_chatbot_id else False,
                                                "script_sequence": chat.sequence,
                                            }
                                        )
                                    elif (
                                            current__chat_seq_script
                                            and current__chat_seq_script.parent_id
                                            and current__chat_seq_script.parent_id
                                            == chat.parent_id
                                    ):
                                        for chat in chatbot_script_lines:
                                            channel.write(
                                                {
                                                    "wa_chatbot_id": chat.whatsapp_chatbot_id.id,
                                                    "script_sequence": chat.sequence,
                                                }
                                            )
                                    else:
                                        first_script = (
                                            self.env["whatsapp.chatbot"]
                                            .search([("id", "=", channel.wa_chatbot_id.id)])
                                            .mapped("step_type_ids")
                                            .filtered(lambda l: l.sequence == 1)
                                        )
                                        for chat in first_script:
                                            channel.write(
                                                {
                                                    "wa_chatbot_id": chat.whatsapp_chatbot_id.id,
                                                    "script_sequence": first_script.sequence,
                                                }
                                            )
                                    if chat.step_call_type == "message":
                                        chat_answer = chat.answer

                                        if not self.env.context.get("whatsapp_application"):
                                            message_values = {
                                                "body": "<p> " + chat_answer + "</p>",
                                                "author_id": user_partner.id,
                                                "email_from": user_partner.email or "",
                                                "model": "discuss.channel",
                                                "message_type": "wa_msgs",
                                                "wa_message_id": vals.get("message_id"),
                                                "isWaMsgs": True,
                                                "subtype_id": self.env["ir.model.data"]
                                                .sudo()
                                                ._xmlid_to_res_id("mail.mt_comment"),
                                                "partner_ids": [(4, partner_id.id)],
                                                "res_id": channel.id,
                                                "reply_to": partner_id.email,
                                                "company_id": vals.get("company_id"),
                                                "wa_chatbot_id": chat.whatsapp_chatbot_id.id,
                                            }
                                            message = (
                                                self.env["mail.message"]
                                                .sudo()
                                                .with_context({"provider_id": provider_id})
                                                .create(message_values)
                                            )
                                            channel._notify_thread(message, message_values)

                                            # comment due to thread single message and message replace issue.
                                            # notifications = [(channel, 'discuss.channel/new_message',
                                            #                   {'id': channel.id, 'message': message_values})]
                                            # self.env["bus.bus"]._sendmany(notifications)

                                            if "message_parent_id" in self.env.context:
                                                parent_msg = (
                                                    self.env["mail.message"]
                                                    .sudo()
                                                    .search(
                                                        [
                                                            (
                                                                "id",
                                                                "=",
                                                                self.env.context.get(
                                                                    "message_parent_id"
                                                                ).id,
                                                            )
                                                        ]
                                                    )
                                                )
                                                answer = provider_id.send_message(
                                                    partner_id,
                                                    chat_answer,
                                                    parent_msg.wa_message_id,
                                                )
                                            else:
                                                answer = provider_id.send_message(
                                                    partner_id, chat_answer
                                                )
                                            if answer.status_code == 200:
                                                dict = json.loads(answer.text)
                                                if (
                                                        provider_id.provider == "graph_api"
                                                ):  # if condition for Graph API
                                                    if (
                                                            "messages" in dict
                                                            and dict.get("messages")
                                                            and dict.get("messages")[0].get(
                                                        "id"
                                                    )
                                                    ):
                                                        dict.get("messages")[0].get("id")
                                                else:
                                                    if "sent" in dict and dict.get("sent"):
                                                        dict["id"]
                                                        if self.env.context.get(
                                                                "wa_messsage_id"
                                                        ):
                                                            self.env.context.get(
                                                                "wa_messsage_id"
                                                            ).wa_message_id = dict["id"]
                                                    else:
                                                        if not self.env.context.get("cron"):
                                                            if "message" in dict:
                                                                raise UserError(
                                                                    dict.get("message")
                                                                )
                                                            if "error" in dict:
                                                                raise UserError(
                                                                    dict.get(
                                                                        "error"
                                                                    ).get("message")
                                                                )
                                                        else:
                                                            vals.update({"type": "fail"})
                                                            if "error" in dict:
                                                                vals.update(
                                                                    {
                                                                        "fail_reason": dict.get(
                                                                            "error"
                                                                        ).get(
                                                                            "message"
                                                                        )
                                                                    }
                                                                )

                                    if chat.step_call_type == "template":
                                        template = chat.template_id
                                        if not self.env.context.get("whatsapp_application"):
                                            if template:
                                                wa_message_values = {}
                                                if template.body_html != "":
                                                    wa_message_values.update(
                                                        {
                                                            "body": tools.html2plaintext(
                                                                template.body_html
                                                            )
                                                        }
                                                    )

                                                wa_message_values.update(
                                                    {
                                                        "author_id": user_partner.id,
                                                        "email_from": user_partner.email
                                                                      or "",
                                                        "model": "discuss.channel",
                                                        "message_type": "wa_msgs",
                                                        "isWaMsgs": True,
                                                        "subtype_id": self.env[
                                                            "ir.model.data"
                                                        ]
                                                        .sudo()
                                                        ._xmlid_to_res_id(
                                                            "mail.mt_comment"
                                                        ),
                                                        "partner_ids": [
                                                            (4, user_partner.id)
                                                        ],
                                                        "res_id": channel.id,
                                                        "reply_to": user_partner.email,
                                                        "wa_chatbot_id": chat.whatsapp_chatbot_id.id,
                                                    }
                                                )

                                                wa_attach_message = (
                                                    self.env["mail.message"]
                                                    .sudo()
                                                    .with_user(provider_id.user_id.id)
                                                    .with_context(
                                                        {
                                                            "template_send": True,
                                                            "wa_template": template,
                                                            "active_model_id": channel.id,
                                                            "active_model": "discuss.channel",
                                                            "active_model_id_chat_bot": partner_id.id,
                                                            "active_model_chat_bot": "res.partner",
                                                            "provider_id": provider_id,
                                                        }
                                                    )
                                                    .create(wa_message_values)
                                                )  # 'attachment_ids': template.attachment_ids.ids,

                                                channel._notify_thread(wa_attach_message, wa_message_values)
                                            # comment due to thread single message and message replace issue.

                                        #             notifications = [(channel, 'discuss.channel/new_message',
                                        #                               {'id': channel.id, 'message': wa_message_values})]
                                        #             self.env["bus.bus"]._sendmany(notifications)
                                        #
                                    if chat.step_call_type == "interactive":
                                        template = chat.template_id

                                        if not self.env.context.get("whatsapp_application"):
                                            user_partner = provider_id.user_id.partner_id

                                            message_values = {
                                                "body": tools.html2plaintext(
                                                    template.body_html
                                                ),
                                                "author_id": user_partner.id,
                                                "email_from": partner_id.email or "",
                                                "model": "discuss.channel",
                                                "message_type": "wa_msgs",
                                                "isWaMsgs": True,
                                                "subtype_id": self.env["ir.model.data"]
                                                .sudo()
                                                ._xmlid_to_res_id("mail.mt_comment"),
                                                "partner_ids": [(4, partner_id.id)],
                                                "res_id": channel.id,
                                                "reply_to": partner_id.email,
                                                "wa_chatbot_id": chat.whatsapp_chatbot_id.id,
                                            }
                                            if template:
                                                wa_message_body = (
                                                    self.env["mail.message"]
                                                    .with_user(provider_id.user_id.id)
                                                    .with_context(
                                                        {
                                                            "template_send": True,
                                                            "wa_template": template,
                                                            "provider_id": provider_id,
                                                            "user_id": provider_id.user_id,
                                                        }
                                                    )
                                                    .create(message_values)
                                                )
                                            else:
                                                wa_message_body = (
                                                    self.env["mail.message"]
                                                    .sudo()
                                                    .with_context(
                                                        {"provider_id": provider_id}
                                                    )
                                                    .create(message_values)
                                                )

                                            channel._notify_thread(wa_message_body, message_values)
                                            # comment due to thread single message and message replace issue.
                                            # notifications = [(channel, 'discuss.channel/new_message',
                                            #                   {'id': channel.id, 'message': message_values})]
                                            # self.env["bus.bus"]._sendmany(notifications)

                                    if chat.step_call_type == "action":

                                        if chat.action_id:
                                            if (
                                                    chat.action_id.binding_model_id.model
                                                    == "crm.lead"
                                            ):

                                                lead_message = "Your lead have been created successfully"
                                                message_values = {
                                                    "body": lead_message,
                                                    "author_id": user_partner.id,
                                                    "email_from": user_partner.email or "",
                                                    "model": "discuss.channel",
                                                    "message_type": "wa_msgs",
                                                    "wa_message_id": vals.get("message_id"),
                                                    "isWaMsgs": True,
                                                    "subtype_id": self.env["ir.model.data"]
                                                    .sudo()
                                                    ._xmlid_to_res_id("mail.mt_comment"),
                                                    "partner_ids": [(4, partner_id.id)],
                                                    "res_id": channel.id,
                                                    "reply_to": partner_id.email,
                                                    "company_id": vals.get("company_id"),
                                                    "wa_chatbot_id": chat.whatsapp_chatbot_id.id,
                                                }
                                                message = (
                                                    self.env["mail.message"]
                                                    .sudo()
                                                    .with_user(provider_id.user_id.id)
                                                    .with_context(
                                                        {"provider_id": provider_id}
                                                    )
                                                    .create(message_values)
                                                )
                                                channel._notify_thread(message, message_values)
                                                # comment due to thread single message and message replace issue.
                                                # notifications = [(channel, 'discuss.channel/new_message',
                                                #                   {'id': channel.id, 'message': message_values})]
                                                # self.env["bus.bus"]._sendmany(notifications)

                                                lead = (
                                                    self.env["crm.lead"]
                                                    .with_user(provider_id.user_id.id)
                                                    .sudo()
                                                    .create(
                                                        {
                                                            "name": partner_id.name
                                                                    + " WA ChatBot Lead ",
                                                            "partner_id": partner_id.id,
                                                            "mobile": partner_id.mobile,
                                                            "user_id": provider_id.user_id.id,
                                                            "type": "lead",
                                                            "description": "Lead Description",
                                                        }
                                                    )
                                                )

                                                if lead:
                                                    if channel:
                                                        channel.write(
                                                            {
                                                                "is_chatbot_ended": True,
                                                                "wa_chatbot_id": False,
                                                            }
                                                        )
                                                        active_operator = provider_id.company_id.wa_chatbot_id.mapped(
                                                            "user_ids"
                                                        ).filtered(
                                                            lambda user: user.im_status
                                                                         == "online"
                                                        )

                                                        if active_operator:
                                                            available_operator = False
                                                            wa_chatbot_channels = provider_id.company_id.wa_chatbot_id.mapped(
                                                                "channel_ids"
                                                            )
                                                            for (
                                                                    wa_channel
                                                            ) in wa_chatbot_channels:
                                                                operators = active_operator.filtered(
                                                                    lambda av_user: av_user.partner_id
                                                                                    not in wa_channel.channel_member_ids.partner_id
                                                                )
                                                                if operators:
                                                                    for (
                                                                            operator
                                                                    ) in operators:
                                                                        available_operator = (
                                                                            operator.partner_id
                                                                        )
                                                                else:
                                                                    available_operator = (
                                                                        active_operator[
                                                                            0
                                                                        ].partner_id
                                                                    )

                                                            if available_operator:
                                                                channel.write(
                                                                    {
                                                                        "channel_partner_ids": [
                                                                            (
                                                                                4,
                                                                                available_operator.id,
                                                                            )
                                                                        ]
                                                                    }
                                                                )
                                                                mail_channel_partner = (
                                                                    self.env[
                                                                        "discuss.channel.member"
                                                                    ]
                                                                    .sudo()
                                                                    .search(
                                                                        [
                                                                            (
                                                                                "channel_id",
                                                                                "=",
                                                                                channel.id,
                                                                            ),
                                                                            (
                                                                                "partner_id",
                                                                                "=",
                                                                                available_operator.id,
                                                                            ),
                                                                        ]
                                                                    )
                                                                )
                                                                mail_channel_partner.write(
                                                                    {"is_pinned": True}
                                                                )
                                                        else:
                                                            channel.write(
                                                                {
                                                                    "is_chatbot_ended": False,
                                                                    "wa_chatbot_id": chat.whatsapp_chatbot_id.id,
                                                                }
                                                            )

                                            if (
                                                    chat.action_id.binding_model_id.model
                                                    == "discuss.channel"
                                            ):
                                                available_operator = False

                                                active_operator = provider_id.company_id.wa_chatbot_id.mapped(
                                                    "user_ids"
                                                ).filtered(
                                                    lambda user: user.im_status == "online"
                                                )

                                                if active_operator:
                                                    wa_chatbot_channels = provider_id.company_id.wa_chatbot_id.mapped(
                                                        "channel_ids"
                                                    )
                                                    for wa_channel in wa_chatbot_channels:
                                                        operators = active_operator.filtered(
                                                            lambda av_user: av_user.partner_id
                                                                            not in wa_channel.channel_member_ids.partner_id
                                                        )
                                                        if operators:
                                                            for operator in operators:
                                                                available_operator = (
                                                                    operator.partner_id
                                                                )
                                                        else:
                                                            available_operator = (
                                                                active_operator[
                                                                    0
                                                                ].partner_id
                                                            )

                                                    if available_operator:
                                                        if channel.whatsapp_channel:
                                                            channel.write(
                                                                {
                                                                    "channel_partner_ids": [
                                                                        (
                                                                            4,
                                                                            available_operator.id,
                                                                        )
                                                                    ],
                                                                    "is_chatbot_ended": True,
                                                                    "wa_chatbot_id": False,
                                                                }
                                                            )
                                                            mail_channel_partner = (
                                                                self.env[
                                                                    "discuss.channel.member"
                                                                ]
                                                                .sudo()
                                                                .search(
                                                                    [
                                                                        (
                                                                            "channel_id",
                                                                            "=",
                                                                            channel.id,
                                                                        ),
                                                                        (
                                                                            "partner_id",
                                                                            "=",
                                                                            available_operator.id,
                                                                        ),
                                                                    ]
                                                                )
                                                            )
                                                            mail_channel_partner.write(
                                                                {"is_pinned": True}
                                                            )

                                                        user_message = "We are getting you our expert please wait"

                                                        message_values = {
                                                            "body": "<p> "
                                                                    + user_message
                                                                    + "</p>",
                                                            "author_id": user_partner.id,
                                                            "email_from": user_partner.email
                                                                          or "",
                                                            "model": "discuss.channel",
                                                            "message_type": "wa_msgs",
                                                            "wa_message_id": vals.get(
                                                                "message_id"
                                                            ),
                                                            "isWaMsgs": True,
                                                            "subtype_id": self.env[
                                                                "ir.model.data"
                                                            ]
                                                            .sudo()
                                                            ._xmlid_to_res_id(
                                                                "mail.mt_comment"
                                                            ),
                                                            "partner_ids": [
                                                                (4, partner_id.id)
                                                            ],
                                                            "res_id": channel.id,
                                                            "reply_to": partner_id.email,
                                                            "company_id": vals.get(
                                                                "company_id"
                                                            ),
                                                            "wa_chatbot_id": chat.whatsapp_chatbot_id.id,
                                                        }
                                                        message = (
                                                            self.env["mail.message"]
                                                            .sudo()
                                                            .with_context(
                                                                {"provider_id": provider_id}
                                                            )
                                                            .create(message_values)
                                                        )
                                                        notifications = [(channel, 'discuss.channel/new_message',
                                                                          {'id': channel.id,
                                                                           'message': message_values})]
                                                        self.env["bus.bus"]._sendmany(
                                                            notifications
                                                        )

                                                        answer = provider_id.send_message(
                                                            partner_id, user_message
                                                        )
                                                        if answer.status_code == 200:
                                                            dict = json.loads(answer.text)
                                                            if (
                                                                    provider_id.provider
                                                                    == "graph_api"
                                                            ):  # if condition for Graph API
                                                                if (
                                                                        "messages" in dict
                                                                        and dict.get("messages")
                                                                        and dict.get(
                                                                    "messages"
                                                                )[0].get("id")
                                                                ):
                                                                    dict.get("messages")[
                                                                        0
                                                                    ].get("id")
                                                            else:
                                                                if (
                                                                        "sent" in dict
                                                                        and dict.get("sent")
                                                                ):
                                                                    dict["id"]
                                                                    if self.env.context.get(
                                                                            "wa_messsage_id"
                                                                    ):
                                                                        self.env.context.get(
                                                                            "wa_messsage_id"
                                                                        ).wa_message_id = dict[
                                                                            "id"
                                                                        ]
                                                                else:
                                                                    if not self.env.context.get(
                                                                            "cron"
                                                                    ):
                                                                        if (
                                                                                "message"
                                                                                in dict
                                                                        ):
                                                                            raise UserError(
                                                                                dict.get(
                                                                                    "message"
                                                                                )
                                                                            )
                                                                        if "error" in dict:
                                                                            raise UserError(
                                                                                dict.get(
                                                                                    "error"
                                                                                ).get(
                                                                                    "message"
                                                                                )
                                                                            )
                                                                    else:
                                                                        vals.update(
                                                                            {"type": "fail"}
                                                                        )
                                                                        if "error" in dict:
                                                                            vals.update(
                                                                                {
                                                                                    "fail_reason": dict.get(
                                                                                        "error"
                                                                                    ).get(
                                                                                        "message"
                                                                                    )
                                                                                }
                                                                            )

                                                        user_message = (
                                                                "Yor are now chatting with "
                                                                + available_operator.name
                                                        )

                                                        message_values = {
                                                            "body": "<p> "
                                                                    + user_message
                                                                    + "</p>",
                                                            "author_id": user_partner.id,
                                                            "email_from": user_partner.email
                                                                          or "",
                                                            "model": "discuss.channel",
                                                            "message_type": "wa_msgs",
                                                            "wa_message_id": vals.get(
                                                                "message_id"
                                                            ),
                                                            "isWaMsgs": True,
                                                            "subtype_id": self.env[
                                                                "ir.model.data"
                                                            ]
                                                            .sudo()
                                                            ._xmlid_to_res_id(
                                                                "mail.mt_comment"
                                                            ),
                                                            "partner_ids": [
                                                                (4, partner_id.id)
                                                            ],
                                                            "res_id": channel.id,
                                                            "reply_to": partner_id.email,
                                                            "company_id": vals.get(
                                                                "company_id"
                                                            ),
                                                            "wa_chatbot_id": chat.whatsapp_chatbot_id.id,
                                                        }
                                                        message = (
                                                            self.env["mail.message"]
                                                            .sudo()
                                                            .with_context(
                                                                {"provider_id": provider_id}
                                                            )
                                                            .create(message_values)
                                                        )
                                                        notifications = [(channel, 'discuss.channel/new_message',
                                                                          {'id': channel.id,
                                                                           'message': message_values})]
                                                        self.env["bus.bus"]._sendmany(
                                                            notifications
                                                        )

                                                        answer = provider_id.send_message(
                                                            partner_id, user_message
                                                        )
                                                        if answer.status_code == 200:
                                                            dict = json.loads(answer.text)
                                                            if (
                                                                    provider_id.provider
                                                                    == "graph_api"
                                                            ):  # if condition for Graph API
                                                                if (
                                                                        "messages" in dict
                                                                        and dict.get("messages")
                                                                        and dict.get(
                                                                    "messages"
                                                                )[0].get("id")
                                                                ):
                                                                    dict.get("messages")[
                                                                        0
                                                                    ].get("id")
                                                            else:
                                                                if (
                                                                        "sent" in dict
                                                                        and dict.get("sent")
                                                                ):
                                                                    dict["id"]
                                                                    if self.env.context.get(
                                                                            "wa_messsage_id"
                                                                    ):
                                                                        self.env.context.get(
                                                                            "wa_messsage_id"
                                                                        ).wa_message_id = dict[
                                                                            "id"
                                                                        ]
                                                                else:
                                                                    if not self.env.context.get(
                                                                            "cron"
                                                                    ):
                                                                        if (
                                                                                "message"
                                                                                in dict
                                                                        ):
                                                                            raise UserError(
                                                                                dict.get(
                                                                                    "message"
                                                                                )
                                                                            )
                                                                        if "error" in dict:
                                                                            raise UserError(
                                                                                dict.get(
                                                                                    "error"
                                                                                ).get(
                                                                                    "message"
                                                                                )
                                                                            )
                                                                    else:
                                                                        vals.update(
                                                                            {"type": "fail"}
                                                                        )
                                                                        if "error" in dict:
                                                                            vals.update(
                                                                                {
                                                                                    "fail_reason": dict.get(
                                                                                        "error"
                                                                                    ).get(
                                                                                        "message"
                                                                                    )
                                                                                }
                                                                            )
                                                else:
                                                    user_message = "Sorry, no active Operator currently available"
                                                    message_values = {
                                                        "body": "<p> "
                                                                + user_message
                                                                + "</p>",
                                                        "author_id": user_partner.id,
                                                        "email_from": user_partner.email
                                                                      or "",
                                                        "model": "discuss.channel",
                                                        "message_type": "wa_msgs",
                                                        "wa_message_id": vals.get(
                                                            "message_id"
                                                        ),
                                                        "isWaMsgs": True,
                                                        "subtype_id": self.env[
                                                            "ir.model.data"
                                                        ]
                                                        .sudo()
                                                        ._xmlid_to_res_id(
                                                            "mail.mt_comment"
                                                        ),
                                                        "partner_ids": [(4, partner_id.id)],
                                                        "res_id": channel.id,
                                                        "reply_to": partner_id.email,
                                                        "company_id": vals.get(
                                                            "company_id"
                                                        ),
                                                        "wa_chatbot_id": chat.whatsapp_chatbot_id.id,
                                                    }
                                                    message = (
                                                        self.env["mail.message"]
                                                        .sudo()
                                                        .with_context(
                                                            {"provider_id": provider_id}
                                                        )
                                                        .create(message_values)
                                                    )
                                                    notifications = [(channel, 'discuss.channel/new_message',
                                                                      {'id': channel.id, 'message': message_values})]
                                                    self.env["bus.bus"]._sendmany(
                                                        notifications
                                                    )

                                                    answer = provider_id.send_message(
                                                        partner_id, user_message
                                                    )
                                                    if answer.status_code == 200:
                                                        dict = json.loads(answer.text)
                                                        if (
                                                                provider_id.provider
                                                                == "graph_api"
                                                        ):  # if condition for Graph API
                                                            if (
                                                                    "messages" in dict
                                                                    and dict.get("messages")
                                                                    and dict.get("messages")[
                                                                0
                                                            ].get("id")
                                                            ):
                                                                dict.get("messages")[0].get(
                                                                    "id"
                                                                )
                                                        else:
                                                            if "sent" in dict and dict.get(
                                                                    "sent"
                                                            ):
                                                                dict["id"]
                                                                if self.env.context.get(
                                                                        "wa_messsage_id"
                                                                ):
                                                                    self.env.context.get(
                                                                        "wa_messsage_id"
                                                                    ).wa_message_id = dict[
                                                                        "id"
                                                                    ]
                                                            else:
                                                                if not self.env.context.get(
                                                                        "cron"
                                                                ):
                                                                    if "message" in dict:
                                                                        raise UserError(
                                                                            dict.get(
                                                                                "message"
                                                                            )
                                                                        )
                                                                    if "error" in dict:
                                                                        raise UserError(
                                                                            dict.get(
                                                                                "error"
                                                                            ).get(
                                                                                "message"
                                                                            )
                                                                        )
                                                                else:
                                                                    vals.update(
                                                                        {"type": "fail"}
                                                                    )
                                                                    if "error" in dict:
                                                                        vals.update(
                                                                            {
                                                                                "fail_reason": dict.get(
                                                                                    "error"
                                                                                ).get(
                                                                                    "message"
                                                                                )
                                                                            }
                                                                        )

                                                    user_message = (
                                                        "We will getting you soon."
                                                    )
                                                    message_values = {
                                                        "body": "<p> "
                                                                + user_message
                                                                + "</p>",
                                                        "author_id": user_partner.id,
                                                        "email_from": user_partner.email
                                                                      or "",
                                                        "model": "discuss.channel",
                                                        "message_type": "wa_msgs",
                                                        "wa_message_id": vals.get(
                                                            "message_id"
                                                        ),
                                                        "isWaMsgs": True,
                                                        "subtype_id": self.env[
                                                            "ir.model.data"
                                                        ]
                                                        .sudo()
                                                        ._xmlid_to_res_id(
                                                            "mail.mt_comment"
                                                        ),
                                                        "partner_ids": [(4, partner_id.id)],
                                                        "res_id": channel.id,
                                                        "reply_to": partner_id.email,
                                                        "company_id": vals.get(
                                                            "company_id"
                                                        ),
                                                        "wa_chatbot_id": chat.whatsapp_chatbot_id.id,
                                                    }
                                                    message = (
                                                        self.env["mail.message"]
                                                        .sudo()
                                                        .with_context(
                                                            {"provider_id": provider_id}
                                                        )
                                                        .create(message_values)
                                                    )
                                                    notifications = [(channel, 'discuss.channel/new_message',
                                                                      {'id': channel.id, 'message': message_values})]
                                                    self.env["bus.bus"]._sendmany(
                                                        notifications
                                                    )

                                                    answer = provider_id.send_message(
                                                        partner_id, user_message
                                                    )
                                                    if answer.status_code == 200:
                                                        dict = json.loads(answer.text)
                                                        if (
                                                                provider_id.provider
                                                                == "graph_api"
                                                        ):  # if condition for Graph API
                                                            if (
                                                                    "messages" in dict
                                                                    and dict.get("messages")
                                                                    and dict.get("messages")[
                                                                0
                                                            ].get("id")
                                                            ):
                                                                dict.get("messages")[0].get(
                                                                    "id"
                                                                )
                                                        else:
                                                            if "sent" in dict and dict.get(
                                                                    "sent"
                                                            ):
                                                                dict["id"]
                                                                if self.env.context.get(
                                                                        "wa_messsage_id"
                                                                ):
                                                                    self.env.context.get(
                                                                        "wa_messsage_id"
                                                                    ).wa_message_id = dict[
                                                                        "id"
                                                                    ]
                                                            else:
                                                                if not self.env.context.get(
                                                                        "cron"
                                                                ):
                                                                    if "message" in dict:
                                                                        raise UserError(
                                                                            dict.get(
                                                                                "message"
                                                                            )
                                                                        )
                                                                    if "error" in dict:
                                                                        raise UserError(
                                                                            dict.get(
                                                                                "error"
                                                                            ).get(
                                                                                "message"
                                                                            )
                                                                        )
                                                                else:
                                                                    vals.update(
                                                                        {"type": "fail"}
                                                                    )
                                                                    if "error" in dict:
                                                                        vals.update(
                                                                            {
                                                                                "fail_reason": dict.get(
                                                                                    "error"
                                                                                ).get(
                                                                                    "message"
                                                                                )
                                                                            }
                                                                        )

            else:
                res = super(WhatsappHistory, self).create(vals)

            return res
