from odoo import api, fields, models, _


class Variables(models.Model):
    _name = "variables"
    _description = 'Whatsapp Variables'

    # def _get_model_fields(self):
    #     domain = []
    #     if self._context and self._context.get('default_model_id'):
    #         domain = [('model_id', '=', self._context.get('default_model_id'))]
    #     return domain

    field_id = fields.Many2one('ir.model.fields','Field')
    component_id = fields.Many2one('components')
    model_id = fields.Many2one('ir.model', related="component_id.model_id")
    sequence = fields.Integer('Sequence', compute='get_seq')

    @api.depends('component_id.variables_ids')
    def get_seq(self):
        for i, rec in enumerate(self.component_id.variables_ids):
            rec.sequence = i + 1