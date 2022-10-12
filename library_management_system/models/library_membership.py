# -*- coding: utf-8 -*-
# Powered by Kanak Infosystems LLP.
# © 2020 Kanak Infosystems LLP. (<https://www.kanakinfosystems.com>).


from odoo import models, fields, api, _
from datetime import timedelta
from odoo.exceptions import UserError


class Membership(models.Model):
    _name = "library.membership"
    _description = "Library Membership"

    def _get_partner_id(self):
        if self._context.get('active_id'):
            return self.env['library.membership'].browse(self._context.get('active_id')).partner_id.id

    name = fields.Char(default="New")
    partner_id = fields.Many2one("res.partner", string="Student Name", required=True, domain=[
        ('is_member', '=', False)], default=_get_partner_id)
    phone_number = fields.Char(required=True)
    email_address = fields.Char(required=True)
    products = fields.Many2one("product.product", domain=[(
        'is_membership_product', '=', True)], string="Membership")
    membership_type = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('half_yearly', 'Half Yearly'),
        ('yearly', 'Yearly')], required=True)
    start_date = fields.Date(string="Membership Start",
                             default=fields.Date.today(), required=True)
    end_date = fields.Date(string="Membership End", required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
        ('expired', 'Expired')], default="draft")
    company_id = fields.Many2one(
        'res.company', default=lambda self: self.env.company)
    paid_membership = fields.Boolean(
        related='company_id.paid_membership_company', readonly=False)
    create_invoice_bool = fields.Boolean()
    invoice_id = fields.Many2one('account.move')
    membership_price = fields.Float(
        "Membership Price", compute="_get_membership_price")
    issued_record_count = fields.Integer(compute="_get_issued_record_count")

    def _get_issued_record_count(self):
        for rec in self:
            if rec.partner_id:
                rec.issued_record_count = self.env['book.issue'].search_count(
                    [('partner_id', '=', rec.partner_id.id)])
            else:
                rec.issued_record_count = 0

    @api.depends('company_id', 'paid_membership', 'membership_type')
    def _get_membership_price(self):
        for rec in self:
            if rec.paid_membership and rec.membership_type:
                if rec.membership_type == 'monthly':
                    rec.membership_price = rec.company_id.monthly_price if rec.paid_membership else 0.0
                elif rec.membership_type == 'quarterly':
                    rec.membership_price = rec.company_id.quarterly_price if rec.paid_membership else 0.0
                elif rec.membership_type == 'half_yearly':
                    rec.membership_price = rec.company_id.half_yearly_price if rec.paid_membership else 0.0
                else:
                    rec.membership_price = rec.company_id.yearly_price if rec.paid_membership else 0.0
            else:
                rec.membership_price = 0.0

    def _cron_membership_expire_reminder(self):
        members = self.env['library.membership'].search(
            [('state', '=', 'done')])
        for member in members:
            ctx = {}
            if (member.end_date - timedelta(days=7)) == fields.Date.today() and member.email:
                if member.end_date == fields.Date.today():
                    member.state = 'expired'
                ctx['email_to'] = member.email_address
                ctx['email_from'] = self.env.user.company_id.email
                ctx['send_mail'] = True
                ctx['company_id'] = self.env.user.company_id
                ctx['record'] = member
                template = self.env.ref(
                    'library_management_system.email_template_for_membership_expire_reminder')
                template.with_context(ctx).send_mail(
                    self.id, force_send=True, raise_exception=False)

    def action_create_invoice(self):
        self.create_invoice_bool = True
        move = self.env['account.move'].create({
            'partner_id': self.partner_id,
            'invoice_date': self.start_date,
            'move_type': 'out_invoice',
            'l10n_in_gst_treatment': 'consumer',
            'membership_id': self.id,
            'state': 'draft',
        })
        move_line = self.env['account.move.line'].create({
            'move_id': move.id,
            'product_id': self.products.id,
            'name': self.membership_type,
            'account_id': self.products.categ_id.property_account_income_categ_id.id,
            'price_unit': self.membership_price,
        })
        prices = move.invoice_line_ids._get_price_total_and_subtotal()
        move_line.price_subtotal = prices['price_subtotal']

        for rec in self:
            rec.state = 'done'
            rec.partner_id.is_member = True
            rec.partner_id.membership = rec.membership_type
            rec.partner_id.membership_exp_date = rec.end_date

    def invoice_button(self):
        return {
            'name': _("Invoices"),
            'res_model': "account.move",
            'view_mode': "tree,form",
            'domain': [('membership_id', '=', self.id)],
            'type': "ir.actions.act_window",
        }

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.phone_number = self.partner_id.phone
            self.email_address = self.partner_id.email

    def action_confirm(self):
        for rec in self:
            rec.state = 'done'
            rec.partner_id.is_member = True
            rec.partner_id.membership = rec.membership_type
            rec.partner_id.membership_exp_date = rec.end_date

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancel'
            rec.partner_id.is_member = False

    @api.onchange('start_date', 'membership_type')
    def _onchange_end_date(self):
        if self.start_date and self.membership_type:
            if self.membership_type == 'monthly':
                self.end_date = self.start_date + timedelta(days=30)
            elif self.membership_type == 'quarterly':
                self.end_date = self.start_date + timedelta(days=90)
            elif self.membership_type == 'half_yearly':
                self.end_date = self.start_date + timedelta(days=180)
            else:
                self.end_date = self.start_date + timedelta(days=360)

    @api.model
    def create(self, values):
        result = super(Membership, self).create(values)
        result['name'] = self.env['ir.sequence'].next_by_code(
            'library.membership')
        return result

    def get_book_issue_records(self):
        return {
            'name': _("Book Issued Record"),
            'res_model': 'book.issue',
            'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.partner_id.id)],
            'type': 'ir.actions.act_window',
        }


class AccountMove(models.Model):
    _inherit = "account.move"

    membership_id = fields.Many2one("library.membership", "Membership")
