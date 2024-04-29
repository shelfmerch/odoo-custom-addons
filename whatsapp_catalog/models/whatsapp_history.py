import json

from odoo import api, models
from odoo.exceptions import UserError


class WhatsAppHistoryInherit(models.Model):
    _inherit = "whatsapp.history"

    # def _get_template_values(self, sales_order=None, message=None, catalogue_id=None):
    #     a = 1
    #     if sales_order and message and catalogue_id:
    #         temp_body = catalogue_id.payment_template.components_ids.filtered(lambda x: x.type == 'body').text
    #         variables_ids = catalogue_id.payment_template.components_ids.filtered(lambda x: x.type != 'buttons').variables_ids
    #         var_length = len(variables_ids)
    #         for length, variable in zip(range(var_length), variables_ids):
    #             st = '{{%d}}' % (length + 1)
    #             if variable.field_id.model == sales_order._name:
    #                 value = sales_order.read()[0][variable.field_id.name]
    #                 if isinstance(value, tuple):
    #                     value = value[1]
    #                     temp_body = temp_body.replace(st, str(value))
    #                 else:
    #                     temp_body = temp_body.replace(st, str(value))
    #         return temp_body
    #     else:
    #         return False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            provider_id = self.env["provider"].browse(
                int(vals.get("provider_id", False))
            )
            partner_id = self.env["res.partner"].browse(
                int(vals.get("partner_id", False))
            )
            # if self.env.context.get("active_model",''):
            #     sale_order = self.env[
            #         self.env.context.get("active_model")
            #     ].browse(self.env.context.get("active_model_id"))
            #     catalogue_id = self.env["wa.catalogue"].search(
            #     [("model_id", "=", sale_order._name)]
            #     )
            #
            # message = self._get_template_values(sales_order=sale_order, catalogue_id=catalogue_id, message=vals['message'])
            # if message:
            #     vals['message'] = message

            if provider_id and partner_id and partner_id.mobile:
                partner_id.write(
                    {"mobile": partner_id.mobile.strip("+").replace(" ", "")}
                )
                part_lst = []
                part_lst.append(partner_id.id)
                if partner_id.id != vals.get("author_id"):
                    part_lst.append(int(vals.get("author_id")))
                if not self.env.context.get("whatsapp_application"):
                    if "template_send" in self.env.context and self.env.context.get(
                            "template_send"
                    ):
                        wa_template = self.env.context.get("wa_template")
                        params = []
                        if (
                                wa_template.template_type == "interactive"
                                and wa_template.components_ids.filtered(
                            lambda x: x.type == "interactive"
                                      and x.interactive_type == "order_details"
                        )
                        ):
                            for component in wa_template.components_ids.filtered(
                                    lambda x: x.type == "interactive"
                                              and x.interactive_type == "order_details"
                            ):
                                template_dict = {}
                                sale_order = self.env[
                                    self.env.context.get("active_model")
                                ].browse(self.env.context.get("active_model_id"))
                                catalogue_id = self.env["wa.catalogue"].search(
                                    [("model_id", "=", sale_order._name)]
                                )
                                items = []
                                offset = 100
                                for val in sale_order.order_line:
                                    dicts = {
                                        "retailer_id": val.product_id.id,
                                        "name": val.product_id.name,
                                        "amount": {
                                            "value": val.price_unit * offset,
                                            "offset": offset,
                                        },
                                        "quantity": val.product_uom_qty,
                                    }
                                    items.append(dicts)
                                action = {}
                                if catalogue_id.payment_type == "upi":
                                    action.update(
                                        {
                                            "name": "review_and_pay",
                                            "parameters": {
                                                "reference_id": sale_order.name,
                                                "type": "digital-goods",
                                                "payment_type": catalogue_id.payment_type,
                                                # "payment_settings": [
                                                #     {
                                                #         "type": "payment_gateway",
                                                #         "payment_gateway": {
                                                #             "type": "razorpay",
                                                #             "configuration_name": "Razorpay_WhatsApp_Account",
                                                #             # "razorpay": {
                                                #             #     "receipt": sale_order.name,
                                                #             #     # "notes": {
                                                #             #     #     "key1": "value1"
                                                #             #     # }
                                                #             # }
                                                #         }
                                                #     }
                                                # # ],
                                                "payment_configuration": catalogue_id.payment_configuration_name,
                                                "currency": "INR",
                                                "total_amount": {
                                                    "value": sale_order.amount_total
                                                             * offset,
                                                    "offset": offset,
                                                },
                                                "order": {
                                                    "status": "pending",
                                                    "items": items,
                                                    "subtotal": {
                                                        "value": sale_order.amount_untaxed
                                                                 * offset,
                                                        "offset": offset,
                                                    },
                                                    "tax": {
                                                        "value": sale_order.amount_tax
                                                                 * offset,
                                                        "offset": offset,
                                                        "description": ",".join(
                                                            sale_order.order_line.tax_id.mapped(
                                                                "display_name"
                                                            )
                                                        ),
                                                    },
                                                    "discount": {
                                                        "value": sum(
                                                            sale_order.order_line.mapped(
                                                                "discount"
                                                            )
                                                        )
                                                                 * offset,
                                                        "offset": offset,
                                                        "description": "Discount",
                                                    },
                                                },
                                            },
                                        }
                                    )
                                elif catalogue_id.payment_type == "razorpay":
                                    action.update(
                                        {
                                            "name": "review_and_pay",
                                            "parameters": {
                                                "reference_id": sale_order.name,
                                                "type": "digital-goods",
                                                # "payment_type": catalogue_id.payment_type,
                                                "payment_settings": [
                                                    {
                                                        "type": "payment_gateway",
                                                        "payment_gateway": {
                                                            "type": "razorpay",
                                                            "configuration_name": catalogue_id.payment_configuration_name,
                                                            "razorpay": {
                                                                "receipt": sale_order.name,
                                                                # "notes": {
                                                                #     "key1": "TEMP1"
                                                                # }
                                                            },
                                                        },
                                                    }
                                                ],
                                                # "payment_configuration": catalogue_id.payment_configuration_name,
                                                "currency": "INR",
                                                "total_amount": {
                                                    "value": sale_order.amount_total
                                                             * offset,
                                                    "offset": offset,
                                                },
                                                "order": {
                                                    "status": "pending",
                                                    "items": items,
                                                    "subtotal": {
                                                        "value": sale_order.amount_untaxed
                                                                 * offset,
                                                        "offset": offset,
                                                    },
                                                    "tax": {
                                                        "value": sale_order.amount_tax
                                                                 * offset,
                                                        "offset": offset,
                                                        "description": ",".join(
                                                            sale_order.order_line.tax_id.mapped(
                                                                "display_name"
                                                            )
                                                        ),
                                                    },
                                                    "discount": {
                                                        "value": sum(
                                                            sale_order.order_line.mapped(
                                                                "discount"
                                                            )
                                                        )
                                                                 * offset,
                                                        "offset": offset,
                                                        "description": "Discount",
                                                    },
                                                },
                                            },
                                        }
                                    )
                                elif catalogue_id.payment_type == "payU":
                                    action.update(
                                        {
                                            "name": "review_and_pay",
                                            "parameters": {
                                                "reference_id": sale_order.name,
                                                "type": "digital-goods",
                                                "payment_type": catalogue_id.payment_type,
                                                # "payment_settings": [
                                                #     {
                                                #         "type": "payment_gateway",
                                                #         "payment_gateway": {
                                                #             "type": "razorpay",
                                                #             "configuration_name": "Razorpay_WhatsApp_Account",
                                                #             # "razorpay": {
                                                #             #     "receipt": sale_order.name,
                                                #             #     # "notes": {
                                                #             #     #     "key1": "value1"
                                                #             #     # }
                                                #             # }
                                                #         }
                                                #     }
                                                # # ],
                                                "payment_configuration": catalogue_id.payment_configuration_name,
                                                "currency": "INR",
                                                "total_amount": {
                                                    "value": sale_order.amount_total
                                                             * offset,
                                                    "offset": offset,
                                                },
                                                "order": {
                                                    "status": "pending",
                                                    "items": items,
                                                    "subtotal": {
                                                        "value": sale_order.amount_untaxed
                                                                 * offset,
                                                        "offset": offset,
                                                    },
                                                    "tax": {
                                                        "value": sale_order.amount_tax
                                                                 * offset,
                                                        "offset": offset,
                                                        "description": ",".join(
                                                            sale_order.order_line.tax_id.mapped(
                                                                "display_name"
                                                            )
                                                        ),
                                                    },
                                                    "discount": {
                                                        "value": sum(
                                                            sale_order.order_line.mapped(
                                                                "discount"
                                                            )
                                                        )
                                                                 * offset,
                                                        "offset": offset,
                                                        "description": "Discount",
                                                    },
                                                },
                                            },
                                        }
                                    )

                                if bool(action):
                                    params.append(action)

                            answer = provider_id.send_mpm_template(
                                wa_template.name,
                                wa_template.lang.iso_code,
                                wa_template.namespace,
                                partner_id,
                                params,
                            )
                            vals["is_commerce_manager"] = True
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

                return super(WhatsAppHistoryInherit, self).create(vals)
