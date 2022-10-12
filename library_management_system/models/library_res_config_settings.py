# -*- coding: utf-8 -*-
# Powered by Kanak Infosystems LLP.
# © 2020 Kanak Infosystems LLP. (<https://www.kanakinfosystems.com>).

from odoo import fields, models, api


class ResCompany(models.Model):
    _inherit = "res.company"

    due_amount_company = fields.Float()
    return_days_company = fields.Integer()
    paid_membership_company = fields.Boolean(string='Paid membership')
    request_period_limit = fields.Integer()
    monthly_price = fields.Float(string="Monthly Membership Price")
    quarterly_price = fields.Float(string="Quarterly Membership Price")
    half_yearly_price = fields.Float(string="Half Yearly Membership Price")
    yearly_price = fields.Float(string="Yearly Membership Price")


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    due_amount = fields.Float(
        related="company_id.due_amount_company", readonly=False, string="Due Amount")
    return_days = fields.Integer(
        related="company_id.return_days_company", readonly=False, string="Return Days")
    paid_membership = fields.Boolean(
        related='company_id.paid_membership_company', readonly=False, string="Paid Membership")
    request_period_limit = fields.Integer(
        related="company_id.request_period_limit", readonly=False, string="Request Period Limit")
    monthly_price = fields.Float(
        string="Monthly Membership Price", related="company_id.monthly_price", readonly=False)
    quarterly_price = fields.Float(
        string="Quarterly Membership Price", related="company_id.quarterly_price", readonly=False)
    half_yearly_price = fields.Float(
        string="Half Yearly Membership Price", related="company_id.half_yearly_price", readonly=False)
    yearly_price = fields.Float(
        string="Yearly Membership Price", related="company_id.yearly_price", readonly=False)
