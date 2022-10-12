# -*- coding: utf-8 -*-
# Powered by Kanak Infosystems LLP.
# © 2020 Kanak Infosystems LLP. (<https://www.kanakinfosystems.com>).

from odoo import models, fields, api, _
from datetime import timedelta
from odoo.exceptions import UserError, ValidationError


class BookRequest(models.Model):
    _name = "book.request"
    _description = "Book Request"

    test = fields.Char()
    name = fields.Char(default="New", readonly=True, required=True)
    partner_id = fields.Many2one("res.partner", string="Student", domain=[
        ('is_member', '=', True)], required=True)
    email = fields.Char(default=lambda self: self.partner_id.email)
    date = fields.Date(string="Request Date", default=fields.Date.today())
    membership_id = fields.Char(readonly=True)
    membership_exp_date = fields.Date(readonly=True)
    product_id = fields.Many2one("product.template", string="Book", domain=[
        ('is_book', '=', True), ('qty_available', '!=', 0.0)])
    state = fields.Selection([
        ('sent', 'Sent'),
        ('confirm', 'Confirm'),
        ('approved', 'Approved'),
        ('done', 'Done'),
        ('rejected', 'Rejected')], default="sent")
    reason = fields.Text()
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company)
    issue_id = fields.Many2one("book.issue")
    user_id = fields.Many2one("res.users", default=lambda self: self.env.user)
    picking_type_id = fields.Many2one(
        'stock.picking.type', string='Picking Type Id')

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.membership_id = self.partner_id.membership
            self.membership_exp_date = self.partner_id.membership_exp_date
            self.email = self.partner_id.email

    @api.model
    def create(self, vals):
        result = super(BookRequest, self).create(vals)
        result['name'] = self.env['ir.sequence'].next_by_code('book.request')
        return result

    def action_confirm(self):
        for rec in self:
            rec.state = 'confirm'

    def action_approve(self):
        ctx = {
            'email_to': self.email,
            'email_from': self.env.user.company_id.email,
            'send_mail': True,
            'partner_name': self.partner_id.name,
            'book_name': self.product_id.name,
            'company_id': self.company_id,
        }
        template = self.env.ref(
            'library_management_system.email_template_for_approve_request')
        template.with_context(ctx).send_mail(
            self.id, force_send=True, raise_exception=False)
        self.state = 'approved'

    def action_reject(self):
        return {
            'name': _('Reject Reason'),
            'res_model': 'book.request.rejected',
            'view_mode': 'form',
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    def issued_records(self):
        return {
            'name': _('Issued Record'),
            'res_model': 'book.issue',
            'view_mode': 'tree',
            'domain': [('id', '=', self.issue_id.id)],
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    def action_issue(self):
        if self.picking_type_id.id == False:
            raise ValidationError('Please Select Picking Type')
        else:
            book_issue = self.env['book.issue'].create({
                'partner_id': self.partner_id.id,
                'issue_date': fields.Date.today(),
                'membership_id': self.membership_id,
                'membership_exp_date': self.membership_exp_date,
                'picking_type_id': self.picking_type_id.id,
                'book_request_origin': self.id,
            })
            line = self.env['book.issue.line'].create({
                'product_id': self.product_id.id,
                'book_title': self.product_id.book_title,
                'author_ids': [res.id for res in self.product_id.author_ids],
                'return_date': fields.Date.today() + timedelta(self.product_id.return_days),
                'quantity': 1,
                'available_quantity': self.product_id.qty_available-1,
                'state': 'issued',
            })
            book_issue.write({'book_line_ids': line})
            book_issue.action_confirm()
            self.state = 'done'
            self.issue_id = book_issue

    def _cron_book_issue_request_rejection(self):
        for rec in self.env['book.request'].search([('state', '=', 'approved')]):
            if (fields.Date.today() - rec.date).days >= 3:
                ctx = {
                    'email_to': rec.email,
                    'email_from': self.env.user.company_id.email,
                    'send_mail': True,
                    'partner_name': rec.partner_id.name,
                    'book_name': rec.product_id.name,
                    'reason': "of Automatically Rejected",
                    'company_id': rec.company_id,
                }
                template = self.env.ref(
                    'library_management_system.email_template_for_request_rejection')
                template.with_context(ctx).send_mail(
                    rec.id, force_send=True, raise_exception=False)
                rec.state = "rejected"
                rec.reason = "Automatically Rejected"


class RequestReject(models.TransientModel):
    _name = "book.request.rejected"
    _description = "Book Request Rejected"

    reason_for_rejection = fields.Text(
        string="Reason for Rejection", required=True)

    def action_confirm(self):
        record = self.env['book.request'].search(
            [('id', '=', self._context.get('active_ids'))])
        ctx = {
            'email_to': record.email,
            'email_from': self.env.user.company_id.email,
            'send_mail': True,
            'partner_name': record.partner_id.name,
            'book_name': record.product_id.name,
            'reason': self.reason_for_rejection,
            'company_id': record.company_id,
        }
        template = self.env.ref(
            'library_management_system.email_template_for_request_rejection')
        template.with_context(ctx).send_mail(
            self.id, force_send=True, raise_exception=False)
        record.state = 'rejected'
        record.reason = self.reason_for_rejection
