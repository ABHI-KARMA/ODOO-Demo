# -*- coding: utf-8 -*-
# Powered by Kanak Infosystems LLP.
# © 2020 Kanak Infosystems LLP. (<https://www.kanakinfosystems.com>).

from odoo import models, fields, api
from datetime import timedelta
from odoo.addons.http_routing.models.ir_http import slug


class ProductTemplate(models.Model):
    _inherit = "product.template"

    # Book Product Details
    is_membership_product = fields.Boolean(string='Is Membership?')
    is_book = fields.Boolean(string="Is a book?")
    book_title = fields.Char()
    book_summary = fields.Text()
    author_ids = fields.Many2many("book.author")
    page_number = fields.Char()
    available_language_ids = fields.Many2many("res.lang")
    isbn_13 = fields.Char(string='ISBN-13')
    publisher_info = fields.Char()
    copyright_owner = fields.Char()
    category_ids = fields.Many2many("book.category")
    issued_lines = fields.One2many(
        "issue.line", "product_template_id", compute="_compute_issued_lines")
    return_days = fields.Integer(string="Book Return Days", required=True,
                                 default=lambda self: self.env.user.company_id.return_days_company, readonly=False)
    due_exceed_amount = fields.Float(
        string="Due Date Exceed Amount", required=True, default=lambda self: self.env.user.company_id.due_amount_company, readonly=False)

    def _compute_issued_lines(self):
        for record in self:
            issed_books = self.env['book.issue'].search([])
            issue_line = []
            for line in issed_books.book_line_ids.filtered(lambda x: x.product_id.id == record.id):
                issue_id = self.env['issue.line'].create({
                    'issue_id': line.issue_id.id,
                    'partner_id': line.issue_id.partner_id.id,
                    'user_id': line.issue_id.user_id.id,
                    'issued_quantity': line.quantity,
                    'issued_date': line.issue_id.issue_date,
                    'return_date': line.issue_id.issue_date + timedelta(days=line.product_id.return_days),
                    'status': line.issue_id.state,
                })
                issue_line.append(issue_id.id)
            if issue_line:
                record.issued_lines = issue_line
            else:
                record.issued_lines = None

    def _compute_website_url(self):
        super(ProductTemplate, self)._compute_website_url()
        for product in self:
            if product.id and product.is_book:
                product.website_url = "/library/book/%s" % slug(product)
            else:
                product.website_url = "/shop/%s" % slug(product)


class IssuedLines(models.Model):
    _name = "issue.line"
    _description = "Issue Line"

    issue_id = fields.Many2one("book.issue")
    partner_id = fields.Many2one("res.partner", string="Member")
    user_id = fields.Many2one("res.users")
    issued_quantity = fields.Float(string="No. of Copies")
    issued_date = fields.Date()
    return_date = fields.Date()
    product_template_id = fields.Many2one("product.template")
    status = fields.Char()
