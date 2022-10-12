# -*- coding: utf-8 -*-
# Powered by Kanak Infosystems LLP.
# © 2020 Kanak Infosystems LLP. (<https://www.kanakinfosystems.com>).

from odoo import fields, models, api
from odoo.exceptions import UserError


class BookReport(models.TransientModel):
    _name = "book.issue.report"
    _description = "Book Issue Report"

    book_ids = fields.Many2many("product.template", domain=[
                                ('is_book', '=', True)])
    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)

    @api.onchange('date_from', 'date_to')
    def _onchange_date(self):
        if self.date_to and self.date_from:
            if self.date_to < self.date_from:
                raise UserError("Date To must be greater then Date From")

    def print_pdf(self):
        return self.env.ref("library_management_system.report_action_sale").report_action(self)
