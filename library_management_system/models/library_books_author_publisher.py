# -*- coding: utf-8 -*-
# Powered by Kanak Infosystems LLP.
# © 2020 Kanak Infosystems LLP. (<https://www.kanakinfosystems.com>).

from odoo import models, fields, api


class BookAuthor(models.Model):
    _name = "book.author"
    _description = "Book Author"

    author_image = fields.Binary()
    name = fields.Char(string="Author Name")
    language_id = fields.Many2one("res.lang")
    country_id = fields.Many2one("res.country")
    born = fields.Date()
    died = fields.Date()
    gender = fields.Selection(
        [('male', 'Male'), ('female', 'Female'), ('other', 'Other')])


class BookPublisher(models.Model):
    _name = "book.publisher"
    _description = "Book Publisher"

    publisher_image = fields.Binary()
    name = fields.Char()
