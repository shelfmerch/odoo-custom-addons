import json
import phonenumbers
from phonenumbers.phonenumberutil import region_code_for_country_code
from odoo import http
from odoo.http import request
from odoo.addons.tus_meta_whatsapp_base.controllers.main_meta import WebHook2

class WebHook2Ext(WebHook2):
    @http.route()
    def meta_webhook(self, **kw):
        """Inherited for the Event flow"""
        wa_dict = {}
        is_tus_discuss_installed = (
            request.env["ir.module.module"]
            .sudo()
            .search([("state", "=", "installed"), ("name", "=", "tus_meta_wa_discuss")])
        )
        if not is_tus_discuss_installed:
            return wa_dict
        data = json.loads(request.httprequest.data.decode("utf-8"))
        wa_dict.update({"messages": data.get("messages")})
        phone_number_id = ""
        if (
            data
            and data.get("entry")
            and data.get("entry")[0].get("changes")
            and data.get("entry")[0].get("changes")[0].get("value")
            and data.get("entry")[0].get("changes")[0].get("value").get("metadata")
            and data.get("entry")[0]
            .get("changes")[0]
            .get("value")
            .get("metadata")
            .get("phone_number_id")
        ):
            phone_number_id = (
                data.get("entry")[0]
                .get("changes")[0]
                .get("value")
                .get("metadata")
                .get("phone_number_id")
            )
        provider = (
            request.env["provider"]
            .sudo()
            .search(
                [
                    ("graph_api_authenticated", "=", True),
                    ("graph_api_instance_id", "=", phone_number_id),
                ],
                limit=1,
            )
        )
        self._get_payment_status(data, provider)

        wa_dict.update({"provider": provider})
        if provider.graph_api_authenticated:
            provider.user_id.partner_id
            if (
                data
                and data.get("entry")
                and data.get("entry")[0].get("changes")
                and data.get("entry")[0].get("changes")[0].get("value")
                and data.get("entry")[0].get("changes")[0].get("value").get("messages")
            ):
                for mes in (
                        data.get("entry")[0].get("changes")[0].get("value").get("messages")
                ):
                    number = mes.get("from")
                    messages_id = mes.get("id")
                    wa_dict.update({"chat": True})
                    partners = (
                        request.env["res.partner"]
                        .sudo()
                        .search(["|", ("phone", "=", number), ("mobile", "=", number)])
                    )
                    wa_dict.update({"partners": partners})
                    if not partners:
                        pn = phonenumbers.parse("+" + number)
                        country_code = region_code_for_country_code(pn.country_code)
                        country_id = (
                            request.env["res.country"]
                            .sudo()
                            .search([("code", "=", country_code)], limit=1)
                        )
                        partners = (
                            request.env["res.partner"]
                            .sudo()
                            .create(
                                {
                                    "name": data.get("entry")[0]
                                    .get("changes")[0]
                                    .get("value")
                                    .get("contacts")[0]
                                    .get("profile")
                                    .get("name"),
                                    "country_id": country_id.id,
                                    "is_whatsapp_number": True,
                                    "mobile": number,
                                }
                            )
                        )
                    for partner in partners:
                        if mes.get("type") == "order" and partner:
                            sale_order = (
                                request.env["sale.order"]
                                .sudo()
                                .create(
                                    {
                                        "partner_id": partner.id,
                                        "wa_message_id": messages_id,
                                        "is_whatsapp_so": True,
                                    }
                                )
                            )
                            order = mes.get("order").get("product_items", False)
                            for val in order:
                                # product = request.env['product.template'].sudo().search([('id', '=', 119)])
                                product = (
                                    request.env["product.template"]
                                    .sudo()
                                    .search([("id", "=", val["product_retailer_id"])])
                                )
                                sale_order.order_line.create(
                                    {
                                        "order_id": sale_order.id,
                                        "name": product.name,
                                        "product_id": product.id,
                                        "product_uom_qty": val["quantity"],
                                        "product_uom": product.uom_id.id,
                                        "price_unit": val["item_price"],
                                    }
                                )
                            sale_order.sudo().with_context(
                                provider=provider, template_state="send_payment"
                            )._send_commerce_manager()
        return super().meta_webhook(**kw)

    def _get_payment_status(self, data, provider):
        if data and provider:
            try:
                payment = (
                    data.get("entry")[0]
                    .get("changes")[0]
                    .get("value")
                    .get("messages")[0]
                    .get("interactive")
                    .get("payment")
                )
                payment_status = payment.get("status", "")
                reference_id = payment.get("reference_id", False)
                if payment_status == "success" and reference_id:
                    sale_order = (
                        request.env["sale.order"]
                        .sudo()
                        .search([("name", "=", reference_id)])
                    )
                    # if sale_order and sale_order.state not in ['cancel', 'sale'] :
                    if (
                        sale_order
                        and sale_order.state not in ["cancel", "sale"]
                        and not sale_order.success_payment_transaction
                    ):
                        sale_order.success_payment_transaction = payment.get(
                            "transaction_id", ""
                        )
                        sale_order.is_whatsapp_so = True
                        sale_order.sudo().with_context(
                            provider=provider, template_state="success_payment"
                        )._send_commerce_manager()
            except:
                return False
