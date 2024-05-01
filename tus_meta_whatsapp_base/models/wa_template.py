from odoo import api, fields, models, _
import requests
import json
from odoo.exceptions import UserError, ValidationError
from odoo.modules.module import get_module_resource
import base64
import re


class WATemplate(models.Model):
    _name = "wa.template"
    _inherit = ['mail.render.mixin']
    _description = 'Whatsapp Templates'

    def init(self):
        video_path = get_module_resource('tus_meta_whatsapp_base', 'static/src/video', 'wa-demo-video.mp4')
        attachment = self.env['ir.attachment'].sudo().search([('name', '=', 'demo-wa-video')])
        if not attachment:
            attachment_value = {
                'name': 'demo-wa-video',
                'datas': base64.b64encode(open(video_path, 'rb').read()),
                'mimetype': 'video/mp4',
            }
            attachment = self.env['ir.attachment'].sudo().create(attachment_value)

        pdf_path = get_module_resource('tus_meta_whatsapp_base', 'static/src/pdf', 'TestPDFfile.pdf')
        attachment = self.env['ir.attachment'].sudo().search([('name', '=', 'demo-wa-pdf')])
        if not attachment:
            attachment_value = {
                'name': 'demo-wa-pdf',
                'datas': base64.b64encode(open(pdf_path, 'rb').read()),
                'mimetype': 'application/pdf',
            }
            attachment = self.env['ir.attachment'].sudo().create(attachment_value)

        pdf_path = get_module_resource('tus_meta_whatsapp_base', 'static/src/image', 'whatsapp_default_set.png')
        attachment = self.env['ir.attachment'].sudo().search([('name', '=', 'demo-wa-image')])
        if not attachment:
            attachment_value = {
                'name': 'demo-wa-image',
                'datas': base64.b64encode(open(pdf_path, 'rb').read()),
                'mimetype': 'image/png',
            }
            attachment = self.env['ir.attachment'].sudo().create(attachment_value)

    @api.model
    def default_get(self, fields):
        res = super(WATemplate, self).default_get(fields)
        if not fields or 'model_id' in fields and not res.get('model_id') and res.get('model'):
            res['model_id'] = self.env['ir.model']._get(res['model']).id
        return res

    def _get_current_user_provider(self):
        # Multi Companies and Multi Providers Code Here
        provider_id = self.env.user.provider_ids.filtered(lambda x: x.company_id == self.env.company)
        if provider_id:
            return provider_id[0]
        return False

    name = fields.Char('Name', translate=True, required=True)
    provider_id = fields.Many2one('provider', 'Provider', default=_get_current_user_provider) # default=lambda self: self.env.user.provider_id
    model_id = fields.Many2one(
        'ir.model', string='Applies to',
        help="The type of document this template can be used with", ondelete='cascade', )
    model = fields.Char('Related Document Model', related='model_id.model', index=True, store=True, readonly=True)
    body_html = fields.Html('Body', render_engine='qweb', translate=True, prefetch=True, sanitize=False)
    state = fields.Selection([
        ('draft', 'DRAFT'),
        ('imported', 'IMPORTED'),
        ('added', 'ADDED TEMPLATE'),
    ], string='State', default='draft')
    namespace = fields.Char('Namespace')
    category = fields.Selection([('marketing', 'MARKETING'),
                                 ('utility', 'UTILITY'),
                                 ('authentication', 'AUTHENTICATION')],
                                'Category', default='utility', required=True)
    # language = fields.Char("Language", default="en")
    lang = fields.Many2one("res.lang", "Language",required=True)
    components_ids = fields.One2many('components', 'wa_template_id', 'Components')
    graph_message_template_id = fields.Char(string="Template UID")
    show_graph_message_template_id = fields.Boolean(compute='_compute_show_graph_message_template_id')
    template_status = fields.Char(string="Template Status", readonly=True)
    template_type = fields.Selection([('template', 'Template'),
                                      ('interactive', 'Interactive')], string="Template Type")

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        res = super(WATemplate, self).copy(default)
        res.template_status = False
        for component in self.components_ids:
            res_component = component.copy({'wa_template_id': res.id})
            for variable in component.variables_ids:
                variable.copy({'component_id':res_component.id})
        return res

    @api.onchange("name")
    def onchange_name(self):
        for rec in self:
            if rec.name and not re.match("^[A-Za-z0-9_]*$", rec.name):
                raise UserError(_("Template name contains letters, numbers and underscores."))

    @api.constrains('name')
    def _constrain_name(self):
        for rec in self:
            if  rec.name and not re.match("^[A-Za-z0-9_]*$", rec.name):
                raise UserError(_("Template name contains letters, numbers and underscores."))

    @api.depends('provider_id')
    def _compute_show_graph_message_template_id(self):
        for message in self:
            if self.provider_id.provider == 'graph_api':
                message.show_graph_message_template_id = True
            else:
                message.show_graph_message_template_id = False

    @api.depends('model')
    def _compute_render_model(self):
        for template in self:
            template.render_model = template.model

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            res = super(WATemplate, self).create(vals)
            res.name = res.name.lower()
            return res

    def add_whatsapp_template(self):
        components = []
        for component in self.components_ids:
            dict = {}
            if component.type == 'header':
                if component.formate == 'media':
                    IrConfigParam = self.env['ir.config_parameter'].sudo()
                    base_url = IrConfigParam.get_param('web.base.url', False)
                    attachment = False

                    if component.media_type == 'document':
                        attachment = self.env['ir.attachment'].sudo().search([('name', '=', 'demo-wa-pdf')])

                    if component.media_type == 'video':
                        attachment = self.env['ir.attachment'].sudo().search([('name', '=', 'demo-wa-video')])

                    if component.media_type == 'image':
                        attachment = self.env['ir.attachment'].sudo().search([('name', '=', 'demo-wa-image')])

                    if attachment:
                        answer = self.provider_id.graph_api_upload_demo_document(attachment)
                        if answer.status_code == 200:
                            data = json.loads(answer.text)
                            file_handle = data.get('h')
                            dict.update({"example": {
                                "header_handle": [file_handle]
                            }, 'type': component.type.upper(), 'format': component.media_type.upper(), })
                        components.append(dict)

                else:
                    header_text = []
                    for variable in component.variables_ids:
                        header_text.append('Test')
                    if header_text:
                        dict.update({"example": {
                            "header_text": header_text}})
                    if component.text:
                        dict.update({'text': component.text, 'type': component.type.upper(),
                                     'format': component.formate.upper()})
                        components.append(dict)

            elif component.type == 'buttons':
                if component.button_type == 'call_to_action':
                    if (
                            component.type_of_action == 'PHONE_NUMBER' or component.type_of_action == 'URL') and component.is_button_clicked:
                        if component.type_of_action == 'PHONE_NUMBER':
                            dict.update({"type": component.type.upper(),
                                         "buttons": [
                                             {'type': component.type_of_action, 'text': component.button_text,
                                              'phone_number': component.phone_number
                                              }
                                         ]
                                         })
                            components.append(dict)
                        else:
                            if component.url_type == 'static':
                                dict.update({"type": component.type.upper(),
                                             "buttons": [
                                                 {'type': component.type_of_action, 'text': component.button_text,
                                                  'url': component.static_website_url
                                                  }
                                             ]
                                             })
                                components.append(dict)

                            else:
                                button_text = []
                                for variable in component.variables_ids:
                                    button_text.append('Test')
                                dict.update({"type": component.type.upper(),
                                             "buttons": [
                                                 {'type': component.type_of_action, 'text': component.button_text,
                                                  'url': component.dynamic_website_url,
                                                  "example": button_text,
                                                  }
                                             ]
                                             })
                                components.append(dict)

                    elif (
                            component.type_of_action == 'PHONE_NUMBER' or component.type_of_action == 'URL') and not component.is_button_clicked:
                        if component.type_of_action == 'PHONE_NUMBER' and component.type_of_action_2 == 'PHONE_NUMBER':
                            dict.update({"type": component.type.upper(),
                                         "buttons": [
                                             {'type': component.type_of_action, 'text': component.button_text,
                                              'phone_number': component.phone_number
                                              },
                                             {'type': component.type_of_action_2, 'text': component.button_text_2,
                                              'phone_number': component.phone_number_2
                                              }
                                         ]
                                         })
                            components.append(dict)
                        elif component.type_of_action == 'PHONE_NUMBER' and component.type_of_action_2 == 'URL':
                            if component.url_type_2 == 'static':
                                dict.update({"type": component.type.upper(),
                                             "buttons": [
                                                 {'type': component.type_of_action, 'text': component.button_text,
                                                  'phone_number': component.phone_number
                                                  },
                                                 {'type': component.type_of_action_2, 'text': component.button_text_2,
                                                  'url': component.static_website_url_2
                                                  }
                                             ]
                                             })
                                components.append(dict)
                            else:
                                button_text = []
                                for variable in component.variables_ids:
                                    button_text.append('Test')
                                dict.update({"type": component.type.upper(),
                                             "buttons": [
                                                 {'type': component.type_of_action, 'text': component.button_text,
                                                  'phone_number': component.phone_number
                                                  },
                                                 {'type': component.type_of_action_2, 'text': component.button_text_2,
                                                  'url': component.dynamic_website_url_2,
                                                  "example": button_text,
                                                  }
                                             ]
                                             })
                                components.append(dict)
                        elif component.type_of_action == 'URL' and component.type_of_action_2 == 'URL':
                            if component.url_type == 'static' and component.url_type_2 == 'static':
                                dict.update({"type": component.type.upper(),
                                             "buttons": [
                                                 {'type': component.type_of_action, 'text': component.button_text,
                                                  'url': component.static_website_url
                                                  },
                                                 {'type': component.type_of_action_2, 'text': component.button_text_2,
                                                  'url': component.static_website_url_2
                                                  }
                                             ]
                                             })
                                components.append(dict)
                            elif component.url_type == 'static' and component.url_type_2 == 'dynamic':
                                button_text = []
                                for variable in component.variables_ids:
                                    button_text.append('Test')
                                dict.update({"type": component.type.upper(),
                                             "buttons": [
                                                 {'type': component.type_of_action, 'text': component.button_text,
                                                  'url': component.static_website_url
                                                  },
                                                 {'type': component.type_of_action_2, 'text': component.button_text_2,
                                                  'url': component.dynamic_website_url_2,
                                                  "example": button_text,
                                                  }
                                             ]
                                             })
                                components.append(dict)
                            elif component.url_type == 'dynamic' and component.url_type_2 == 'dynamic':
                                button_text = []
                                for variable in component.variables_ids:
                                    button_text.append('Test')
                                dict.update({"type": component.type.upper(),
                                             "buttons": [
                                                 {'type': component.type_of_action, 'text': component.button_text,
                                                  'url': component.dynamic_website_url,
                                                  "example": button_text,
                                                  },
                                                 {'type': component.type_of_action_2, 'text': component.button_text_2,
                                                  'url': component.dynamic_website_url_2,
                                                  "example": button_text,
                                                  }
                                             ]
                                             })
                                components.append(dict)
                            else:
                                button_text = []
                                for variable in component.variables_ids:
                                    button_text.append('Test')
                                dict.update({"type": component.type.upper(),
                                             "buttons": [
                                                 {'type': component.type_of_action, 'text': component.button_text,
                                                  'url': component.dynamic_website_url,
                                                  "example": button_text,
                                                  },
                                                 {'type': component.type_of_action_2, 'text': component.button_text_2,
                                                  'url': component.static_website_url_2,
                                                  "example": button_text,
                                                  }
                                             ]
                                             })
                                components.append(dict)

                        else:
                            if component.url_type == 'static':
                                dict.update({"type": component.type.upper(),
                                             "buttons": [
                                                 {'type': component.type_of_action, 'text': component.button_text,
                                                  'url': component.static_website_url
                                                  },
                                                 {'type': component.type_of_action_2, 'text': component.button_text_2,
                                                  'phone_number': component.phone_number_2
                                                  }
                                             ]
                                             })
                                components.append(dict)
                            else:
                                button_text = []
                                for variable in component.variables_ids:
                                    button_text.append('Test')
                                dict.update({"type": component.type.upper(),
                                             "buttons": [
                                                 {'type': component.type_of_action, 'text': component.button_text,
                                                  'url': component.dynamic_website_url,
                                                  "example": button_text,
                                                  },
                                                 {'type': component.type_of_action_2, 'text': component.button_text_2,
                                                  'phone_number': component.phone_number_2,
                                                  "example": button_text,
                                                  }
                                             ]
                                             })
                                components.append(dict)

                elif component.button_type == 'quick_reply':
                    if component.quick_reply_type == 'custom' and component.is_button_clicked == True and component.is_second_button_clicked == True:
                        if component.quick_reply_type == 'custom':
                            dict.update({"type": component.type.upper(),
                                         "buttons": [
                                             {'type': component.button_type.upper(), 'text': component.button_text,
                                              },
                                         ]
                                         })
                            components.append(dict)

                    elif component.quick_reply_type == 'custom' and component.is_button_clicked == False and component.is_second_button_clicked == True:
                        if component.quick_reply_type_2 == 'custom':
                            dict.update({"type": component.type.upper(),
                                         "buttons": [
                                             {'type': component.button_type.upper(), 'text': component.button_text,
                                              },
                                             {'type': component.button_type.upper(),
                                              'text': component.button_text_2,
                                              }
                                         ]
                                         })
                            components.append(dict)

                    elif component.quick_reply_type == 'custom' and component.is_button_clicked == True and component.is_second_button_clicked == False:
                        if component.quick_reply_type_3 == 'custom':
                            dict.update({"type": component.type.upper(),
                                         "buttons": [
                                             {'type': component.button_type.upper(), 'text': component.button_text,
                                              },
                                             {'type': component.button_type.upper(),
                                              'text': component.button_text_3,
                                              }
                                         ]
                                         })
                            components.append(dict)
                    else:
                        if component.quick_reply_type == 'custom':
                            if component.quick_reply_type_2 == 'custom':
                                if component.quick_reply_type_3 == 'custom':
                                    dict.update({"type": component.type.upper(),
                                                 "buttons": [
                                                     {'type': component.button_type.upper(),
                                                      'text': component.button_text,
                                                      },
                                                     {'type': component.button_type.upper(),
                                                      'text': component.button_text_2,
                                                      },
                                                     {'type': component.button_type.upper(),
                                                      'text': component.button_text_3,
                                                      }
                                                 ]
                                                 })
                                    components.append(dict)

            else:
                body_text = []
                for variable in component.variables_ids:
                    body_text.append('Test')
                if body_text:
                    dict.update({"example": {
                        "body_text": [body_text
                                      ]}})
                if component.text:
                    dict.update({'text': component.text, 'type': component.type.upper(), })
                    components.append(dict)

        if components:

            answer = self.provider_id.add_template(self.name, self.lang.iso_code, self.category.upper(), components)
            if answer.status_code == 200:
                dict = json.loads(answer.text)

                if self.provider_id.provider == 'chat_api':
                    if 'message' in dict:
                        raise UserError(
                            (dict.get('message')))
                    if 'error' in dict:
                        raise UserError(
                            (dict.get('error').get('message')))
                    else:
                        if 'status' in dict and dict.get('status') == 'submitted':
                            self.state = 'added'
                            self.namespace = dict.get('namespace')

                if self.provider_id.provider == 'graph_api':
                    if 'message' in dict:
                        raise UserError(
                            (dict.get('message')))
                    if 'error' in dict:
                        raise UserError(
                            (dict.get('error').get('message')))
                    else:
                        if 'id' in dict:
                            self.state = 'added'
                            self.graph_message_template_id = dict.get('id')
        else:
            raise UserError(
                ("please add components!"))

    def resubmit_whatsapp_template(self):
        components = []
        for component in self.components_ids:
            dict = {}
            if component.type == 'header':
                if component.formate == 'media':
                    IrConfigParam = self.env['ir.config_parameter'].sudo()
                    base_url = IrConfigParam.get_param('web.base.url', False)
                    attachment = False

                    if component.media_type == 'document':
                        attachment = self.env['ir.attachment'].sudo().search([('name', '=', 'demo-wa-pdf')])

                    if component.media_type == 'video':
                        attachment = self.env['ir.attachment'].sudo().search([('name', '=', 'demo-wa-video')])

                    if component.media_type == 'image':
                        attachment = self.env['ir.attachment'].sudo().search([('name', '=', 'demo-wa-image')])

                    if attachment:
                        answer = self.provider_id.graph_api_upload_demo_document(attachment)
                        if answer.status_code == 200:
                            data = json.loads(answer.text)
                            file_handle = data.get('h')
                            dict.update({"example": {
                                "header_handle": [file_handle]
                            }, 'type': component.type.upper(), 'format': component.media_type.upper(), })
                        components.append(dict)

                else:
                    header_text = []
                    for variable in component.variables_ids:
                        header_text.append('Test')
                    if header_text:
                        dict.update({"example": {
                            "header_text": header_text}})
                    if component.text:
                        dict.update({'text': component.text, 'type': component.type.upper(),
                                     'format': component.formate.upper()})
                        components.append(dict)

            elif component.type == 'buttons':
                if component.button_type == 'call_to_action':
                    if (
                            component.type_of_action == 'PHONE_NUMBER' or component.type_of_action == 'URL') and component.is_button_clicked:
                        if component.type_of_action == 'PHONE_NUMBER':
                            dict.update({"type": component.type.upper(),
                                         "buttons": [
                                             {'type': component.type_of_action, 'text': component.button_text,
                                              'phone_number': component.phone_number
                                              }
                                         ]
                                         })
                            components.append(dict)
                        else:
                            if component.url_type == 'static':
                                dict.update({"type": component.type.upper(),
                                             "buttons": [
                                                 {'type': component.type_of_action, 'text': component.button_text,
                                                  'url': component.static_website_url
                                                  }
                                             ]
                                             })
                                components.append(dict)

                            else:
                                button_text = []
                                for variable in component.variables_ids:
                                    button_text.append('Test')
                                dict.update({"type": component.type.upper(),
                                             "buttons": [
                                                 {'type': component.type_of_action, 'text': component.button_text,
                                                  'url': component.dynamic_website_url,
                                                  "example": button_text,
                                                  }
                                             ]
                                             })
                                components.append(dict)

                    elif (
                            component.type_of_action == 'PHONE_NUMBER' or component.type_of_action == 'URL') and not component.is_button_clicked:
                        if component.type_of_action == 'PHONE_NUMBER' and component.type_of_action_2 == 'PHONE_NUMBER':
                            dict.update({"type": component.type.upper(),
                                         "buttons": [
                                             {'type': component.type_of_action, 'text': component.button_text,
                                              'phone_number': component.phone_number
                                              },
                                             {'type': component.type_of_action_2, 'text': component.button_text_2,
                                              'phone_number': component.phone_number_2
                                              }
                                         ]
                                         })
                            components.append(dict)
                        elif component.type_of_action == 'PHONE_NUMBER' and component.type_of_action_2 == 'URL':
                            if component.url_type_2 == 'static':
                                dict.update({"type": component.type.upper(),
                                             "buttons": [
                                                 {'type': component.type_of_action, 'text': component.button_text,
                                                  'phone_number': component.phone_number
                                                  },
                                                 {'type': component.type_of_action_2, 'text': component.button_text_2,
                                                  'url': component.static_website_url_2
                                                  }
                                             ]
                                             })
                                components.append(dict)
                            else:
                                button_text = []
                                for variable in component.variables_ids:
                                    button_text.append('Test')
                                dict.update({"type": component.type.upper(),
                                             "buttons": [
                                                 {'type': component.type_of_action, 'text': component.button_text,
                                                  'phone_number': component.phone_number
                                                  },
                                                 {'type': component.type_of_action_2, 'text': component.button_text_2,
                                                  'url': component.dynamic_website_url_2,
                                                  "example": button_text,
                                                  }
                                             ]
                                             })
                                components.append(dict)
                        elif component.type_of_action == 'URL' and component.type_of_action_2 == 'URL':
                            if component.url_type == 'static' and component.url_type_2 == 'static':
                                dict.update({"type": component.type.upper(),
                                             "buttons": [
                                                 {'type': component.type_of_action, 'text': component.button_text,
                                                  'url': component.static_website_url
                                                  },
                                                 {'type': component.type_of_action_2, 'text': component.button_text_2,
                                                  'url': component.static_website_url_2
                                                  }
                                             ]
                                             })
                                components.append(dict)
                            elif component.url_type == 'static' and component.url_type_2 == 'dynamic':
                                button_text = []
                                for variable in component.variables_ids:
                                    button_text.append('Test')
                                dict.update({"type": component.type.upper(),
                                             "buttons": [
                                                 {'type': component.type_of_action, 'text': component.button_text,
                                                  'url': component.static_website_url
                                                  },
                                                 {'type': component.type_of_action_2, 'text': component.button_text_2,
                                                  'url': component.dynamic_website_url_2,
                                                  "example": button_text,
                                                  }
                                             ]
                                             })
                                components.append(dict)
                            elif component.url_type == 'dynamic' and component.url_type_2 == 'dynamic':
                                button_text = []
                                for variable in component.variables_ids:
                                    button_text.append('Test')
                                dict.update({"type": component.type.upper(),
                                             "buttons": [
                                                 {'type': component.type_of_action, 'text': component.button_text,
                                                  'url': component.dynamic_website_url,
                                                  "example": button_text,
                                                  },
                                                 {'type': component.type_of_action_2, 'text': component.button_text_2,
                                                  'url': component.dynamic_website_url_2,
                                                  "example": button_text,
                                                  }
                                             ]
                                             })
                                components.append(dict)
                            else:
                                button_text = []
                                for variable in component.variables_ids:
                                    button_text.append('Test')
                                dict.update({"type": component.type.upper(),
                                             "buttons": [
                                                 {'type': component.type_of_action, 'text': component.button_text,
                                                  'url': component.dynamic_website_url,
                                                  "example": button_text,
                                                  },
                                                 {'type': component.type_of_action_2, 'text': component.button_text_2,
                                                  'url': component.static_website_url_2,
                                                  "example": button_text,
                                                  }
                                             ]
                                             })
                                components.append(dict)

                        else:
                            if component.url_type == 'static':
                                dict.update({"type": component.type.upper(),
                                             "buttons": [
                                                 {'type': component.type_of_action, 'text': component.button_text,
                                                  'url': component.static_website_url
                                                  },
                                                 {'type': component.type_of_action_2, 'text': component.button_text_2,
                                                  'phone_number': component.phone_number_2
                                                  }
                                             ]
                                             })
                                components.append(dict)
                            else:
                                button_text = []
                                for variable in component.variables_ids:
                                    button_text.append('Test')
                                dict.update({"type": component.type.upper(),
                                             "buttons": [
                                                 {'type': component.type_of_action, 'text': component.button_text,
                                                  'url': component.dynamic_website_url,
                                                  "example": button_text,
                                                  },
                                                 {'type': component.type_of_action_2, 'text': component.button_text_2,
                                                  'phone_number': component.phone_number_2,
                                                  "example": button_text,
                                                  }
                                             ]
                                             })
                                components.append(dict)

                elif component.button_type == 'quick_reply':
                    if component.quick_reply_type == 'custom' and component.is_button_clicked == True and component.is_second_button_clicked == True:
                        if component.quick_reply_type == 'custom':
                            dict.update({"type": component.type.upper(),
                                         "buttons": [
                                             {'type': component.button_type.upper(), 'text': component.button_text,
                                              },
                                         ]
                                         })
                            components.append(dict)

                    elif component.quick_reply_type == 'custom' and component.is_button_clicked == False and component.is_second_button_clicked == True:
                        if component.quick_reply_type_2 == 'custom':
                            dict.update({"type": component.type.upper(),
                                         "buttons": [
                                             {'type': component.button_type.upper(), 'text': component.button_text,
                                              },
                                             {'type': component.button_type.upper(),
                                              'text': component.button_text_2,
                                              }
                                         ]
                                         })
                            components.append(dict)

                    elif component.quick_reply_type == 'custom' and component.is_button_clicked == True and component.is_second_button_clicked == False:
                        if component.quick_reply_type_3 == 'custom':
                            dict.update({"type": component.type.upper(),
                                         "buttons": [
                                             {'type': component.button_type.upper(), 'text': component.button_text,
                                              },
                                             {'type': component.button_type.upper(),
                                              'text': component.button_text_3,
                                              }
                                         ]
                                         })
                            components.append(dict)
                    else:
                        if component.quick_reply_type == 'custom':
                            if component.quick_reply_type_2 == 'custom':
                                if component.quick_reply_type_3 == 'custom':
                                    dict.update({"type": component.type.upper(),
                                                 "buttons": [
                                                     {'type': component.button_type.upper(),
                                                      'text': component.button_text,
                                                      },
                                                     {'type': component.button_type.upper(),
                                                      'text': component.button_text_2,
                                                      },
                                                     {'type': component.button_type.upper(),
                                                      'text': component.button_text_3,
                                                      }
                                                 ]
                                                 })
                                    components.append(dict)

            else:
                body_text = []
                for variable in component.variables_ids:
                    body_text.append('Test')
                if body_text:
                    dict.update({"example": {
                        "body_text": [body_text
                                      ]}})
                if component.text:
                    dict.update({'text': component.text, 'type': component.type.upper(), })
                    components.append(dict)

        if components:
            answer = self.provider_id.resubmit_template(self.category.upper(), self.graph_message_template_id, components)
            if answer.status_code == 200:
                dict = json.loads(answer.text)

                if self.provider_id.provider == 'chat_api':
                    if 'message' in dict:
                        raise UserError(
                            (dict.get('message')))
                    if 'error' in dict:
                        raise UserError(
                            (dict.get('error').get('message')))
                    else:
                        if 'status' in dict and dict.get('status') == 'submitted':
                            self.state = 'added'
                            self.namespace = dict.get('namespace')

                if self.provider_id.provider == 'graph_api':
                    if 'message' in dict:
                        raise UserError(
                            (dict.get('message')))
                    if 'error' in dict:
                        raise UserError(
                            (dict.get('error').get('message')))
                    else:
                        if 'id' in dict:
                            self.state = 'added'
                            self.graph_message_template_id = dict.get('id')
        else:
            raise UserError(
                ("please add components!"))

    def remove_whatsapp_template(self):
        answer = self.provider_id.remove_template(self.name)
        if answer.status_code == 200:
            dict = json.loads(answer.text)
            if 'message' in dict:
                raise UserError(
                    (dict.get('message')))
            if 'error' in dict:
                raise UserError(
                    (dict.get('error').get('message')))
            if 'success' in dict and dict.get('success'):
                self.state = 'draft'

    def get_whatsapp_temaplate(self):
        for provider in self.env['provider'].search([]):
            if provider.chat_api_authenticated:
                response = provider.get_whatsapp_template()
                if response.status_code == 200:
                    dict = json.loads(response.text)
                    for template in dict.get('templates'):
                        if not self.search([('name', '=', template.get('name'))]):
                            if template.get('status') in ['approved', 'submitted']:
                                template_state = 'imported'
                                component_vals_list = []
                                for comp in template.get('components'):
                                    component_type = comp.get('type')
                                    # component_text = comp.get('text')
                                    comp_media_type = comp.get('format')
                                    # comp_formate_type = comp.get('formate')

                                    if component_type == 'HEADER':
                                        if comp_media_type in ['VIDEO', 'DOCUMENT', 'IMAGE', 'TEXT']:
                                            if comp_media_type == 'TEXT':
                                                compoment_ids = self.env['components'].create(
                                                    {'type': comp.get('type').lower(), 'formate': 'TEXT'.lower(),
                                                     'text': comp.get('text')})
                                                component_vals_list.append((4, compoment_ids.id))
                                            else:
                                                compoment_ids = self.env['components'].create(
                                                    {'type': comp.get('type').lower(), 'formate': 'MEDIA'.lower(),
                                                     'media_type': comp.get('format').lower()})
                                                component_vals_list.append((4, compoment_ids.id))
                                    else:
                                        compoment_ids = self.env['components'].create(
                                            {'type': comp.get('type').lower(), 'text': comp.get('text')})
                                        component_vals_list.append((4, compoment_ids.id))

                                vals = {
                                    'name': template.get('name'),
                                    'category': template.get('category').lower(),
                                    'provider_id': provider.id,
                                    'lang': self.env.ref('base.lang_en').id,
                                    'namespace': template.get('namespace'),
                                    'components_ids': component_vals_list,
                                    'state': template_state
                                }
                                self.create(vals)

    def add_imported_whatsapp_template(self):
        self.write({'state': 'added'})

    def get_whatsapp_template_status(self):
        if self.provider_id.graph_api_authenticated:
            base_url = self.provider_id.graph_api_url + self.provider_id.graph_api_business_id + '/message_templates?name=' + self.name + '&access_token=' + self.provider_id.graph_api_token
            headers = {
                "Authorization": self.provider_id.graph_api_token
            }

            try:
                response = requests.get(base_url, headers=headers)
                if response.status_code == 200:
                    response_data = response.json()
                    if response_data['data']:
                        for data in response_data['data']:
                            if self.name == data['name']:
                                status = data['status']
                                self.write({
                                    'template_status': status,
                                    'graph_message_template_id': data['id'],
                                })
                            else:
                                self.write({
                                    'template_status': False
                                })
                    else:
                        self.write({
                            'template_status': False
                        })

            except requests.exceptions.ConnectionError:
                raise UserError(
                    ("please check your internet connection."))
        else:
            raise UserError(
                ("please authenticated your whatsapp."))

    def send_pre_message_by_whatsapp(self):
        active_model = self.model
        provider_id = self.provider_id
        partner_id = self.env.context.get('partner', False)
        if partner_id:
            wizard_rec = self.env['wa.compose.message'].with_context(active_model=active_model,
                                                                        active_id=partner_id).create(
                {'partner_id': partner_id, 'provider_id': provider_id.id,
                 'template_id': self.id})
            wizard_rec.onchange_template_id_wrapper()
            return wizard_rec.send_whatsapp_message()

    def get_all_templates_status(self):
        templates = self.sudo().search([])
        for rec in templates:
            if rec.provider_id.graph_api_authenticated:
                base_url = rec.provider_id.graph_api_url + rec.provider_id.graph_api_business_id + '/message_templates?name=' + rec.name + '&access_token=' + rec.provider_id.graph_api_token
                headers = {
                    "Authorization": rec.provider_id.graph_api_token
                }
                try:
                    response = requests.get(base_url, headers=headers)
                    if response.status_code == 200:
                        response_data = response.json()
                        if response_data['data']:
                            for data in response_data['data']:
                                if rec.name == data['name']:
                                    status = data['status']
                                    rec.write({
                                        'template_status': status,
                                        'graph_message_template_id': data['id'],
                                    })
                                else:
                                    rec.write({
                                        'template_status': False
                                    })
                        else:
                            rec.write({
                                'template_status': False
                            })

                except requests.exceptions.ConnectionError:
                    raise UserError(
                        ("please check your internet connection."))

            else:
                raise UserError(
                    ("please authenticated your whatsapp."))
