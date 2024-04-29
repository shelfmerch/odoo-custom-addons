from odoo import fields, models, api


class InteractiveList(models.Model):
    _name = 'interactive.list'
    _description = 'List for interactive'

    title = fields.Char(string="Title")
    description = fields.Char(string="Description")
    interactive_list_title_id = fields.Many2one(comodel_name="interactive.list.title", invisible=True)


class InteractiveListTitle(models.Model):
    _name = 'interactive.list.title'
    _description = 'List title'

    main_title = fields.Char(string="Title")
    component_id = fields.Many2one(comodel_name="components", invisible=True)
    title_ids = fields.One2many(comodel_name="interactive.list", inverse_name="interactive_list_title_id", string="List")


