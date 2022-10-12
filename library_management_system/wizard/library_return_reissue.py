# -*- coding: utf-8 -*-
# Powered by Kanak Infosystems LLP.
# © 2020 Kanak Infosystems LLP. (<https://www.kanakinfosystems.com>).

from odoo import models, fields, api
from datetime import timedelta
from odoo.exceptions import ValidationError


class ReturnBook(models.TransientModel):
    _name = "return.book"
    _description = "Return Book"

    def _default_book_lines(self):
        record = self.env['book.issue'].search(
            [('id', '=', self._context.get('active_ids'))])
        self.due_date_amount = 10.0
        values = []
        for line in record.book_line_ids.filtered(lambda self: self.state != 'returned'):
            exceed_amt = 0.0
            if line.return_date < fields.Date.today():
                exceed_amt = ((fields.Date.today()-line.return_date).days *
                              line.product_id.due_exceed_amount) * line.quantity
            line_id = self.env['return.line'].create({
                'product_id': line.product_id.id,
                'quantity': line.quantity,
                'return_today': True if line.return_date <= fields.Date.today() else False,
                'exceed_amount': exceed_amt,
            })
            values.append(line_id.id)
        return values

    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company, readonly=True)
    picking_type_id = fields.Many2one("stock.picking.type", default=lambda self: self.env['book.issue'].search(
        [('id', '=', self._context.get('active_ids'))]).picking_type_id.return_picking_type_id)
    book_lines = fields.One2many(
        "return.line", "return_id", default=_default_book_lines)
    current_date = fields.Date(default=fields.Date.today(), readonly=True)
    due_date_amount = fields.Float(string="Due Date Exceed Amount", readonly=True,
                                   default=lambda self: sum(self.book_lines.mapped('exceed_amount')))
    journal_id = fields.Many2one('account.journal', store=True, readonly=False,
                                 domain="[('company_id', '=', company_id), ('type', 'in', ('bank', 'cash'))]")

    def _prepare_stock_move(self, line, record):
        vals = {
            'product_id': line.product_id.product_variant_id.id,
            'product_uom_qty': line.quantity,
            'product_uom': line.product_id.uom_id.id,
            'state': 'draft',
            'name': line.product_id.book_title,
            'date': fields.Datetime.now(),
            'location_id': self.picking_type_id.default_location_src_id.id,
            'location_dest_id': self.picking_type_id.default_location_dest_id.id,
            'picking_type_id': record.picking_type_id.id,
            'warehouse_id': record.picking_type_id.warehouse_id.id,
            'procure_method': 'make_to_stock',
        }
        return vals

    def _prepare_stock_picking(self, record):
        vals = {
            'partner_id': record.partner_id.id,
            'picking_type_id': record.picking_type_id.return_picking_type_id.id,
            'scheduled_date': record.issue_date,
            'date_done': record.issue_date,
            'origin': record.name,
            'move_type': 'direct',
            'user_id': record.user_id.id,
            'company_id': record.company_id.id,
            'location_id': record.picking_type_id.return_picking_type_id.default_location_src_id.id,
            'location_dest_id': record.picking_type_id.return_picking_type_id.default_location_dest_id.id,
        }

    def _send_mail(self, record, book_lines):
        books = []
        for book_line in book_lines:
            if book_line.return_today == True:
                books.append(book_line.product_id)
        if len(books) > 0:
            ctx = {
                'email_to': record.partner_id.email,
                'email_from': self.env.user.company_id.email,
                'send_mail': True,
                'partner_name': record.partner_id.name,
                'book_name': [book.name for book in books],
                'company_id': self.company_id.name,
            }
            template = self.env.ref(
                'library_management_system.email_template_for_return_books')
            template.with_context(ctx).send_mail(
                self.id, force_send=True, raise_exception=False)

    def action_confirm(self):
        record = self.env['book.issue'].search(
            [('id', '=', self._context.get('active_ids'))])
        pickings = []
        for picking_id in record.picking_ids:
            pickings.append(picking_id.id)

        if self.due_date_amount > 0.0:
            payment = self.env['account.payment'].create({
                'payment_type': 'inbound',
                'partner_type': 'customer',
                'partner_id': record.partner_id.id,
                'destination_account_id': 7,
                'company_id': self.env.user.company_id.id,
                'amount': self.due_date_amount,
                'date': self.current_date,
                'journal_id': self.journal_id.id,
                'ref': record.name,
            })
            record.payment_id = payment.id
            payment.action_post()
        picking = self.env['stock.picking'].create({
            'partner_id': record.partner_id.id,
            'picking_type_id': record.picking_type_id.return_picking_type_id.id,
            'scheduled_date': record.issue_date,
            'date_done': record.issue_date,
            'origin': record.name,
            'move_type': 'direct',
            'user_id': record.user_id.id,
            'company_id': record.company_id.id,
            'location_id': record.picking_type_id.return_picking_type_id.default_location_src_id.id,
            'location_dest_id': record.picking_type_id.return_picking_type_id.default_location_dest_id.id,
        })
        picking_line = []
        for line in self.book_lines.filtered(lambda x: x.return_today == True):
            move_line = self.env['stock.move'].create(
                self._prepare_stock_move(line, record))
            picking_line.append(move_line.id)
            # Return Book Status in book.issue.line
            line = self.env['book.issue.line'].search(
                [('issue_id', '=', record.id), ('product_id', '=', line.product_id.id)])
            line.state = 'returned'
        picking.move_ids_without_package = picking_line
        stock_picking = record.confirm_pickings(picking)
        picking.action_confirm()
        # picking.action_assign()
        pickings.append(picking.id)
        record.picking_ids = pickings if pickings else False
        # change the status of Issue.book
        value = record.book_line_ids.mapped('state')
        res = value.count(value[0]) == len(value)
        record.state = 'return' if res else record.state
    # send return book mail
        mail = self._send_mail(record, self.book_lines)


class ReturnLine(models.TransientModel):
    _name = "return.line"
    _description = "Return Line"

    product_id = fields.Many2one("product.template")
    quantity = fields.Integer()
    return_today = fields.Boolean(string="Return Today?")
    return_id = fields.Many2one("return.book")
    exceed_amount = fields.Float()


class ReissueBook(models.TransientModel):
    _name = "reissue.book"
    _description = "Reissue Book"

    def _default_book_lines(self):
        records = self.env['book.issue'].search(
            [('id', '=', self._context.get('active_ids'))])

        values = []
        for line in records.book_line_ids.filtered(lambda self: self.state != 'reissued'):
            line_id = self.env['reissue.line'].create({
                'product_id': line.product_id.id,
                'quantity': line.quantity,
                'reissue_today': True if line.return_date <= fields.Date.today() else False
            })

            values.append(line_id.id)
        return values

    book_lines = fields.One2many(
        "reissue.line", "reissue_id", default=_default_book_lines)

    def action_confirm(self):
        record = self.env['book.issue'].search(
            [('id', '=', self._context.get('active_ids'))])
        if record:
            new_record = self.env['book.issue'].create({
                'partner_id': record.partner_id.id,
                'issue_date': fields.Date.today(),
                'return_date': fields.Date.today() + timedelta(days=15),
                'picking_type_id': record.picking_type_id.id,
                'user_id': record.user_id.id,
                'state': 'issued',
                'name': 'Reissued' + ' ' + record.name,
            })
            lines = []
            if self.book_lines.filtered(lambda self: self.reissue_today == True):
                for line in self.book_lines.filtered(lambda self: self.reissue_today == True):
                    lines.append([0, 0, {
                        'product_id': line.product_id.id,
                        'quantity': line.quantity,
                        'book_title': line.product_id.book_title,
                        'isbn_13': line.product_id.isbn_13,
                        'author_ids': [res.id for res in line.product_id.author_ids],
                        'state':'issued',
                    }])
                    issued_line = self.env['book.issue.line'].search(
                        [('issue_id', '=', record.id), ('product_id', '=', line.product_id.id)])
                    issued_line.state = 'reissued'

                new_record.write({'book_line_ids': lines})

                # change the status of Issue.book
                value = record.book_line_ids.mapped('state')
                res = value.count(value[0]) == len(value)
                record.state = 'reissued' if res else record.state
            else:
                raise ValidationError('Nothing to reissue')


class ReissueLine(models.TransientModel):
    _name = "reissue.line"
    _description = "Reissue Line"

    product_id = fields.Many2one("product.template")
    quantity = fields.Integer()
    reissue_today = fields.Boolean("Reissue?")
    reissue_id = fields.Many2one("reissue.book")
