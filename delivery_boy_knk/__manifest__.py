# -*- coding: utf-8 -*-
# Powered by Kanak Infosystems LLP.
# © 2020 Kanak Infosystems LLP. (<https://www.kanakinfosystems.com>).

{
    'name': 'Delivery Boy',
    'version': '15.0.1.0',
    'summary': '',
    'description': """""",
    'license': 'OPL-1',
    'author': 'Kanak Infosystems LLP.',
    'support': 'info@kanakinfosystems.com',
    'depends': [
        'base',
        'sale_management',
        'stock',
        'website',
        'base_geolocalize',
    ],
    'data': [
        "security/security.xml",
        "security/ir.model.access.csv",

        "views/res_partner_view.xml",
        "views/delivery_control_view.xml",
        "views/sale_order.xml",
        "views/res_company_view.xml",
        "views/template.xml",
        "views/menuitem.xml",

        "data/sequence.xml",
        "data/email_template.xml",

    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
