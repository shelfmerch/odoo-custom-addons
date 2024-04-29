from odoo import api, fields, models, _
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


class Components(models.Model):
    _name = "components"
    _description = 'Whatsapp Components'

    sequence = fields.Integer(string="Sequence")
    type = fields.Selection([('header', 'HEADER'),
                             ('body', 'BODY'),
                             ('footer', 'FOOTER'), ('buttons', 'BUTTONS'),
                             ('interactive', 'INTERACTIVE')],
                            'Type', default='header')
    formate = fields.Selection([('text', 'TEXT'),
                                ('media', 'MEDIA')],
                               'Formate', default='text')
    formate_media_type = fields.Selection([('static', 'Static Media File'),
                                           ('dynamic', 'Dynamic Media File')], string="Format Media Type",
                                          default='dynamic')

    media_type = fields.Selection([('document', 'DOCUMENT'),
                                   ('video', 'VIDEO'),
                                   ('image', 'IMAGE'), ],
                                  'Media Type', default='document')
    attachment_ids = fields.Many2many('ir.attachment', string="Attach Document")

    text = fields.Text('Text')

    variables_ids = fields.One2many('variables', 'component_id', 'Variables')
    wa_template_id = fields.Many2one('wa.template')
    model_id = fields.Many2one('ir.model', related="wa_template_id.model_id")

    button_type = fields.Selection([('none', 'None'),
                                    ('call_to_action', 'Call To Action'),
                                    ('quick_reply', 'Quick Reply')],
                                   'Button Type', default="none")
    type_of_action = fields.Selection([('PHONE_NUMBER', 'Call Phone Number'),
                                       ('URL', 'Visit Website')], 'Type of Action',
                                      default="PHONE_NUMBER")
    button_text = fields.Char(string="Button Text", size=25)
    button_text_2 = fields.Char(string="Button  Text", size=25)
    button_text_3 = fields.Char(string="Button text", size=25)
    phone_number = fields.Char(string="Phone Number", size=20)
    phone_number_2 = fields.Char(string="Phone  Number", size=20)
    url_type = fields.Selection([('static', 'Static'),
                                 ('dynamic', 'Dynamic')], 'URL Type', default="static")
    url_type_2 = fields.Selection([('static', 'Static'),
                                   ('dynamic', 'Dynamic')], 'URL type', default="static")
    name = fields.Char(string='Name', default="a")
    static_website_url = fields.Char(string="Website URL")
    static_website_url_2 = fields.Char(string="Website Url")
    dynamic_website_url = fields.Char(string='Dynamic URL')
    dynamic_website_url_2 = fields.Char(string='Dynamic Url')
    quick_reply_type = fields.Selection([('custom', 'Custom')], string="Quick Reply Type", default="custom")
    quick_reply_type_2 = fields.Selection([('custom', 'Custom')], string="Quick Reply type", default="custom")
    quick_reply_type_3 = fields.Selection([('custom', 'Custom')], string="Quick reply type", default="custom")
    footer_text = fields.Char(string="Footer Text", default="Not interested? Tap Stop promotions")
    type_of_action_2 = fields.Selection([('PHONE_NUMBER', 'Call Phone Number'),
                                         ('URL', 'Visit Website')], 'Type of action', default="URL")
    is_button_clicked = fields.Boolean(string="Is Button Clicked", default=True)
    is_second_button_clicked = fields.Boolean(string="Is Button clicked", default=True)
    interactive_type = fields.Selection([('button', 'BUTTON'),
                                         ('list', 'LIST'),
                                         ('product', 'PRODUCT'),
                                         ('product_list', 'PRODUCT LIST')],
                                        'Interactive Message Type', default='button')
    interactive_list_ids = fields.One2many(comodel_name="interactive.list.title", inverse_name="component_id",
                                           string="List Items")
    interactive_button_ids = fields.One2many(comodel_name="interactive.button", inverse_name="component_id",
                                             string="Button Items")
    interactive_product_list_ids = fields.One2many(comodel_name="interactive.product.list", inverse_name="component_id",
                                                   string="Product List Items")
    catalog_id = fields.Char(string="Catalog ID")
    product_retailer_id = fields.Char(string="Product Retailer ID")

    def add_another_button(self):
        self.is_button_clicked = False

    def delete_button(self):
        self.is_button_clicked = True

    def delete_button_2(self):
        self.is_second_button_clicked = True

    def add_third_button(self):
        self.is_second_button_clicked = False

    @api.onchange("text")
    def onchange_text(self):
        for rec in self:
            if rec.type == 'header' and rec.formate == 'text' and rec.text and len(rec.text) > 60:
                raise UserError(_("60-character limit for headers text."))
            if rec.type == 'body' and rec.formate == 'text' and rec.text and len(rec.text) > 1024:
                raise UserError(_("1,024-character limit for body text."))

    @api.constrains('type', 'formate', 'text')
    def _constrain_text_length(self):
        for rec in self:
            if rec.type == 'header' and rec.formate == 'text' and rec.text and len(rec.text) > 60:
                raise UserError(_("60-character limit for headers text."))
            if rec.type == 'body' and rec.formate == 'text' and rec.text and len(rec.text) > 1024:
                raise UserError(_("1,024-character limit for body text."))

    @api.onchange('attachment_ids')
    def onchange_check_attachment(self):
        for rec in self:
            if rec.attachment_ids:
                for attachment_id in rec.attachment_ids:
                    if rec.formate_media_type == 'static' and rec.media_type == 'document':
                        if attachment_id.mimetype not in document_type:
                            raise ValidationError("Invalid type %s for document" % attachment_id.mimetype)
                    if rec.formate_media_type == 'static' and rec.media_type == 'video':
                        if attachment_id.mimetype not in video_type:
                            raise ValidationError("Invalid type %s for video" % attachment_id.mimetype)
                    if rec.formate_media_type == 'static' and rec.media_type == 'image':
                        if attachment_id.mimetype not in image_type:
                            raise ValidationError("Invalid type %s for image" % attachment_id.mimetype)
