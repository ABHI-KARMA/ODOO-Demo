# -*- coding: utf-8 -*-
# Powered by Kanak Infosystems LLP.
# © 2020 Kanak Infosystems LLP. (<https://www.kanakinfosystems.com>).

from odoo import models, fields, api, _
from datetime import timedelta
from odoo.exceptions import ValidationError
from odoo.tests import Form


class BookIssue(models.Model):
    _name = "book.issue"
    _description = "Book Issue"

    name = fields.Char(default="New", readonly=True)
    partner_id = fields.Many2one(
        "res.partner", string="Member", required=True, domain=[('is_member', '=', True)])
    membership_id = fields.Char()
    membership_exp_date = fields.Date(
        compute='_compute_membership', store=True)
    issue_date = fields.Date(compute='_compute_membership',
                             default=fields.Date.today(), required=True, store=True)
    return_date = fields.Date()
    user_id = fields.Many2one(
        "res.users", default=lambda self: self.env.user.id)
    book_line_ids = fields.One2many(
        "book.issue.line", "issue_id", required=True)
    is_return_today = fields.Boolean()
    picking_ids = fields.Many2many("stock.picking")
    payment_id = fields.Many2one("account.payment")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('issued', 'Issued'),
        ('return', 'Return'),
        ('reissued', 'Reissued'),
        ('cancel', 'Cancel')], default="draft")
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company)
    picking_count = fields.Integer(compute="_count_pickings")
    is_paid = fields.Boolean(compute="_get_payment")
    picking_type_id = fields.Many2one("stock.picking.type", required=True)
    book_request_origin = fields.Many2one(
        'book.request', readonly=True)
    book_reservation_origin = fields.Many2one(
        'book.reservation', readonly=True)

    @api.depends('partner_id')
    def _compute_membership(self):
        if self.partner_id:
            self.membership_id = self.partner_id.membership
            self.membership_exp_date = self.partner_id.membership_exp_date

    def _get_payment(self):
        self.is_paid = True if len(self.payment_id) > 0 else False

    @api.depends('picking_ids')
    def _count_pickings(self):
        self.picking_count = len(self.picking_ids) if (
            len(self.picking_ids) > 0) else 0

    def action_confirm(self):
        if len(self.book_line_ids) <= 0:
            raise ValidationError(
                "There is no book issue line, please add it first")
        else:
            self.picking_ids = self.create_stock_pickings(self.state)
            self.state = 'issued'
            for line in self.book_line_ids:
                line.state = 'issued'

    def create_stock_pickings(self, state):
        picking = None
        if state == 'draft':
            picking = self.env['stock.picking'].create({
                'partner_id': self.partner_id.id,
                'picking_type_id': self.picking_type_id.id,
                'scheduled_date': self.issue_date,
                'date_done': self.issue_date,
                'origin': self.name,
                'move_type': 'direct',
                'user_id': self.user_id.id,
                'company_id': self.company_id.id,
                'location_id': self.picking_type_id.default_location_src_id.id,
                'location_dest_id': self.picking_type_id.default_location_dest_id.id,
            })
            picking_line = []
            for line in self.book_line_ids:

                move_line = self.env['stock.move'].create({
                    'product_id': line.product_id.product_variant_id.id,
                    'product_uom_qty': line.quantity,
                    'name': line.product_id.book_title,
                    'date': self.issue_date,
                    'product_uom': line.product_id.uom_id.id,
                    'location_id': self.picking_type_id.default_location_src_id.id,
                    'location_dest_id': self.picking_type_id.default_location_dest_id.id
                })
                picking_line.append(move_line.id)
            picking.move_ids_without_package = picking_line
            stock_picking = self.confirm_pickings(picking)
        return picking

    def confirm_pickings(self, picking):
        if picking:
            picking.action_confirm()
            picking.action_assign()
            action = picking.button_validate()
            wizard = Form(self.env[action['res_model']].with_context(
                action['context'])).save()
            wizard.process()
            return picking

    def action_cancel(self):
        self.state = 'cancel'
        for line in self.book_line_ids:
            line.state = 'cancelled'

    def action_return(self):
        return {
            'name': _('Return Book'),
            'res_model': 'return.book',
            'view_mode': 'form',
            'type': 'ir.actions.act_window',
            'target': 'new'
        }

    def action_reissue(self):
        return {
            'name': _('Reissue Book'),
            'res_model': 'reissue.book',
            'view_mode': 'form',
            'type': 'ir.actions.act_window',
            'target': 'new'
        }

    def _cron_return_date_reminder(self):
        products = [product.id for product in self.env['product.template'].search(
            [('is_book', '=', True)])]

        records = self.env['book.issue.line'].search(
            [('product_id', 'in', products), ('state', 'in', ['issued', 'reissued'])])

        for rec in records:
            ctx = {}
            if (rec.return_date - timedelta(days=1) <= fields.Date.today()):
                if rec.issue_id.partner_id.email:
                    ctx['email_to'] = rec.issue_id.partner_id.email
                    ctx['email_from'] = self.env.user.company_id.email
                    ctx['send_mail'] = True
                    ctx['partner_id'] = rec.issue_id.partner_id.name
                    ctx['record'] = rec
                    template = self.env.ref(
                        'library_management_system.email_template_for_return_date_reminder')
                    template.with_context(ctx).send_mail(
                        self.id, force_send=True, raise_exception=False)

    @api.model
    def create(self, vals):
        result = super(BookIssue, self).create(vals)
        result['name'] = self.env['ir.sequence'].next_by_code('book.issue')
        return result

    def get_picking_ids(self):
        return {
            'name': _('Pickings'),
            'domain': [('id', 'in', [res.id for res in self.picking_ids])],
            'view_mode': 'tree,form',
            'res_model': 'stock.picking',
            'type': 'ir.actions.act_window',
        }

    def get_payment_id(self):
        return {
            'name': _('Payment'),
            'domain': [('id', '=', self.payment_id.id)],
            'view_mode': 'tree,form',
            'res_model': 'account.payment',
            'type': 'ir.actions.act_window',
        }


class BookIssueLine(models.Model):
    _name = "book.issue.line"
    _description = "Book Issue Line"

    product_id = fields.Many2one("product.template", domain=[(
        'is_book', '=', True), ('qty_available', '!=', 0.0)])
    book_title = fields.Char(readonly=True,related="product_id.book_title")
    available_quantity = fields.Float(readonly=True, store=True)
    author_ids = fields.Many2many("book.author", readonly=True,related="product_id.author_ids")
    isbn_13 = fields.Char(string="ISBN-13", readonly=True,related="product_id.isbn_13")
    quantity = fields.Integer(default=1)
    issue_id = fields.Many2one("book.issue")
    issue_date = fields.Date(related="issue_id.issue_date")
    return_date = fields.Date(compute="_compute_return_date")
    state = fields.Selection([('cancelled', 'Cancelled'), ('returned', 'Returned'), (
        'reissued', 'Reissued'), ('issued', 'Issued')], readonly=True)

    @api.depends('product_id')
    def _compute_return_date(self):
        for rec in self:
            if rec.product_id.return_days:
                rec.return_date = fields.Date.today() + timedelta(days=rec.product_id.return_days)
                rec.available_quantity = rec.product_id.qty_available

            else:
                rec.return_date = fields.Date.today(
                ) + timedelta(days=rec.env.company.return_days_company)
                rec.available_quantity = rec.product_id.qty_available

    @api.onchange('quantity')
    def _onchange_quantity(self):
        if self.quantity != 1 and (self.quantity > self.available_quantity):
            raise ValidationError(
                "Quantity should be less than Available Quantity!")
        elif self.quantity <= 0:
            raise ValidationError(
                "Please Select atleast 1 quantity!")
        else:
            pass
