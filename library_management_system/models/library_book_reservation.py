# -*- coding: utf-8 -*-
# Powered by Kanak Infosystems LLP.
# © 2020 Kanak Infosystems LLP. (<https://www.kanakinfosystems.com>).

from odoo import fields, models, api
from datetime import timedelta
from odoo.exceptions import UserError, ValidationError


class BookReservation(models.Model):
    _name = "book.reservation"
    _description = "Book Reservation"

    name = fields.Char(default="New", required=True, readonly=True)
    partner_id = fields.Many2one(
        "res.partner", string="Student Name", required=True, domain=[('is_member', '=', True)])
    date = fields.Date(default=fields.Date.today())
    user_id = fields.Many2one(
        "res.users", default=lambda self: self.env.user.id)
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company)
    membership_id = fields.Char(
        string="Membership ID", compute='_compute_partner_id', readonly=True, store=True)
    membership_exp_date = fields.Date(
        compute='_compute_partner_id', readonly=True, store=True)
    book_ids = fields.One2many("book.reservation.line", "reservation_id")
    state = fields.Selection(
        [('sent', 'Sent'), ('issued', 'Issued')], default="sent")
    issue_id = fields.Many2one("book.issue")
    picking_type_id = fields.Many2one("stock.picking.type")
    picking = fields.Boolean(default=False)

    @api.model
    def create(self, vals):
        result = super(BookReservation, self).create(vals)
        result['name'] = self.env['ir.sequence'].next_by_code(
            'book.reservation')
        return result

    @api.depends('partner_id')
    def _compute_partner_id(self):
        for res in self:
            if res.partner_id:
                res.membership_id = res.partner_id.membership
                res.membership_exp_date = res.partner_id.membership_exp_date
        self.picking = True

    def action_done(self):
        if self.picking_type_id.id == False:
            raise ValidationError('Please Select Picking Type')
        else:

            for res in self.book_ids:
                if res.available_quantity == 0.0:
                    raise UserError("This Book is not available yet")
                else:
                    book_issue = self.env['book.issue'].create({
                        'partner_id': self.partner_id.id,
                        'issue_date': fields.Date.today(),
                        'membership_id': self.membership_id,
                        'membership_exp_date': self.membership_exp_date,
                        'picking_type_id': self.picking_type_id.id,
                        'book_reservation_origin': self.id,

                    })
                    lines = []
                    for rec in self.book_ids:
                        lines.append([0, 0, {
                            'product_id': rec.product_id.id,
                            'book_title': rec.book_title,
                            'author_ids': [res.id for res in rec.author_ids],
                            'return_date':fields.Date.today() + timedelta(rec.product_id.return_days),
                            'quantity':rec.quantity,
                            'available_quantity':rec.product_id.qty_available-1,
                            'state':'issued',
                        }])
                    book_issue.write({'book_line_ids': lines})
                    book_issue.action_confirm()
                    self.state = 'issued'
                    self.issue_id = book_issue


class BookIssueLine(models.Model):
    _name = "book.reservation.line"
    _description = "Book Reservation Line"

    product_id = fields.Many2one("product.template", domain=[(
        'is_book', '=', True), ('qty_available', '=', 0)], string="Book")
    book_title = fields.Char(related="product_id.book_title")
    available_quantity = fields.Float(
        related="product_id.qty_available", string="Available Quantity")
    author_ids = fields.Many2many(
        "book.author",)
    isbn_13 = fields.Char(string='ISBN-13', related="product_id.isbn_13")
    quantity = fields.Integer(default=1)
    state = fields.Selection([('not_available', 'Not Available'),
                              ('available', 'Available')], readonly=True, string="Status")
    reservation_id = fields.Many2one("book.reservation")
    user_id = fields.Many2one(
        "res.users", default=lambda self: self.env.user.id)

    @api.depends('available_quantity')
    def _compute_available_quantity(self):
        for res in self:
            res.available_quantity = res.product_id.qty_available

    def _cron_check_availability(self):
        for rec in self.env['book.reservation.line'].search([('reservation_id.state', '=', 'confirm')]):
            if rec.product_id.qty_available > 0:
                rec.state = 'available'
                rec.available_quantity = rec.product_id.qty_available
            else:
                rec.state = 'not_available'
                rec.available_quantity = 0.0

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.author_ids = self.product_id.author_ids
