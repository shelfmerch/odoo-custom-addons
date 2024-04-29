{
    'name': 'Odoo Meta WhatsApp Discuss | Odoo Whatsapp Bidirectional Integration  | Odoo Meta WhatsApp Graph API | Odoo V17 Community Edition',
    'version': '17.2',
    'author': 'TechUltra Solutions Private Limited',
    'category': 'Discuss',
    'live_test_url': 'https://www.techultrasolutions.com/blog/news-2/odoo-whatsapp-integration-a-boon-for-business-communication-25',
    'company': 'TechUltra Solutions Private Limited',
    'website': "https://www.techultrasolutions.com/",
    'price': 89,
    'currency': 'USD',
    'summary': """whatsapp discuss , Whatsapp bi-directional chat is the whatsapp chat room where user can interact to the customer and bi-directional chat can be done via this module
        Odoo WhatsApp Integration
        Odoo Meta WhatsApp Graph API
        Odoo V17 Community Edition
        Odoo V17 Community WhatsApp Integration
        V17 Community WhatsApp
        Community WhatsApp
        Community
        WhatsApp Community
        Odoo WhatsApp Community
        Odoo WhatsApp Cloud API
        WhatsApp Cloud API
        WhatsApp Community Edition
    """,
    'description': """
        whatsapp chatroom is the functionality where user can use the discuss features of the odoo base to extend that to use the whatsapp communication between the user and customer
        Odoo WhatsApp Integration
        Odoo Meta WhatsApp Graph API
        Odoo V17 Community Edition
        Odoo V17 Community WhatsApp Integration
        V17 Community WhatsApp
        Community WhatsApp
        Community
        WhatsApp Community
        Odoo WhatsApp Community
        Odoo WhatsApp Cloud API
        WhatsApp Cloud API
        WhatsApp Community Edition
    """,
    'depends': ['web', 'tus_meta_whatsapp_base'],
    'data': [
        "data/cron.xml",
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'tus_meta_wa_discuss/static/src/scss/*.scss',
            'tus_meta_wa_discuss/static/src/xml/AgentsList.xml',
            'tus_meta_wa_discuss/static/src/js/common/**/*',
            'tus_meta_wa_discuss/static/src/js/agents/**/*',
            'tus_meta_wa_discuss/static/src/js/templates/**/*',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'images': ['static/description/main_screen.gif'],
}
