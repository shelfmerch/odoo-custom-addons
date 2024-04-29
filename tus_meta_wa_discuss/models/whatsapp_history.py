# -*- coding: utf-8 -*-
from odoo import models, fields, api
from dateutil import tz
from datetime import datetime, timedelta


class ResPartner(models.Model):
    _inherit = 'whatsapp.history'

    def get_template_required_set(self):
        from_zone = tz.gettz('UTC')
        to_zone = tz.gettz(self.env.user.tz)
        utc = datetime.strptime(datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f'), '%Y-%m-%d %H:%M:%S.%f')
        utc = utc.replace(tzinfo=from_zone)
        date_obj = utc.astimezone(to_zone)
        last_date_obj = date_obj - timedelta(hours=23)
        history_partner_ids = self.env['whatsapp.history'].sudo().search(
            [('create_date', '<=', date_obj), ('create_date', '>=', last_date_obj), ('type', '=', 'received'),('partner_id','=',self.partner_id.id)]).mapped(
            'partner_id')
        history_partner_ids.write({'send_template_req': False})

        if not history_partner_ids:
            self.partner_id.write({'send_template_req':True})