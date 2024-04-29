from odoo import _, api, fields, models, modules, tools
import requests
import json
from odoo.exceptions import UserError, ValidationError,AccessError

class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_whatsapp_number = fields.Boolean('Is Whatsapp Number')
    channel_provider_line_ids = fields.One2many('channel.provider.line', 'partner_id', 'Channel Provider Line')

    def check_whatsapp_history(self):
        self.ensure_one()
        return {
            "name": _("Whatsapp History"),
            "type": "ir.actions.act_window",
            "res_model": "whatsapp.history",
            "view_mode": "tree",
            "domain": [("partner_id", "=", self.id)],
        }

    @api.model
    def im_search(self, name, limit=20, excluded_ids=None):
        """ Search partner with a name and return its id, name and im_status.
            Note : the user must be logged
            :param name : the partner name to search
            :param limit : the limit of result to return
        """
        # This method is supposed to be used only in the context of channel creation or
        # extension via an invite. As both of these actions require the 'create' access
        # right, we check this specific ACL.
        if self.env['discuss.channel'].check_access_rights('create', raise_exception=False):
            name = '%' + name + '%'
            excluded_partner_ids = [self.env.user.partner_id.id]
            self.env.cr.execute("""
                            SELECT
                                P.id as id,
                                P.name as name
                            FROM res_partner P
                            WHERE P.name ILIKE %s
                                AND P.id NOT IN %s
                            LIMIT %s
                        """, (name, tuple(excluded_partner_ids), limit))
            return self.env.cr.dictfetchall()
        else:
            return {}

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            res = super(ResPartner, self).create(vals)
            # phone change to mobile
            if res.mobile:
                res.mobile = res.mobile.strip('+').replace(" ", "").replace("-", "")
            return res

    def write(self, vals):
        if 'mobile' in vals:
            if vals.get('mobile'):
                vals.update({'mobile':vals.get('mobile').strip('+').replace(" ", "")})
        res= super(ResPartner, self).write(vals)
        return res

