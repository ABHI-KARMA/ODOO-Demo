# -*- coding: utf-8 -*-
# Powered by Kanak Infosystems LLP.
# © 2020 Kanak Infosystems LLP. (<https://www.kanakinfosystems.com>).


from odoo import models, fields


class ResPartner(models.Model):
    _inherit = "res.partner"

    is_member = fields.Boolean(store=True)
    membership = fields.Char()
    membership_exp_date = fields.Date()
