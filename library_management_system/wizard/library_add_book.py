# -*- coding: utf-8 -*-
# Powered by Kanak Infosystems LLP.
# © 2020 Kanak Infosystems LLP. (<https://www.kanakinfosystems.com>).

from odoo import models, fields, api
from isbntools.app import *
import isbnlib
from odoo.exceptions import ValidationError


class AddBooks(models.TransientModel):
    _name = "library.add.book.wizard"
    _description = "Library Add Book Wizard"

    isbn = fields.Char()

    is_valid_book = fields.Boolean()
    book_image = fields.Binary()
    book_title = fields.Char()
    author_ids = fields.Many2many("book.author")
    publisher_id = fields.Many2one("book.publisher")
    year = fields.Char()
    return_days = fields.Integer()
    due_date_exceed_amount = fields.Float()
    description = fields.Text()

    def _get_authors(self, authors_dict):
        authors = []
        for author in authors_dict:
            if author not in [res.name for res in
                              self.env['book.author'].search([])]:
                val = self.env['book.author'].create({'name': author})
                authors.append(val.id)
            else:
                authors.append(self.env['book.author'].search(
                    [('name', '=', author)]).id)
        return authors

    @api.onchange('isbn')
    def _onchange_isbn_13(self):
        book = {}
        try:
            book = isbnlib.meta(self.isbn)
        except Exception as e:
            print(e)
        if book:
            self.is_valid_book = True
            self.book_title = book['Title']
            self.author_ids = self._get_authors(book['Authors'])
            self.publisher_id = self.write({'publisher_id': book['Publisher']})
            self.year = book['Year']
        else:
            self.is_valid_book = False
            if self.isbn:
                raise ValidationError(f"There is no book with this ISBN {self.isbn}")

    def add_book(self):
        book = {}
        try:
            book = isbnlib.meta(self.isbn)
        except Exception as e:
            print(e)
        product = self.env['product.template'].search(
            [('is_book', '=', True), ('isbn_13', '=', book['ISBN-13'])])
        if product:
            raise ValidationError("This book is already Exists")
        else:
            self.env['product.template'].create({
                'name': book['Title'],
                'type': 'product',
                'is_book': True,
                'book_title': book['Title'],
                'author_ids': self._get_authors(book['Authors']),
                'isbn_13': book['ISBN-13'],
                'publisher_info': self.env['book.publisher'].search([('name', '=', book['Publisher'])]).name or '' + " " + book['Year'] or '',
                'due_exceed_amount': self.due_date_exceed_amount,
                'return_days': self.return_days,
                'description': self.description,
            })
