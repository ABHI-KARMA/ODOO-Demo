# -*- coding: utf-8 -*-
# Powered by Kanak Infosystems LLP.
# © 2020 Kanak Infosystems LLP. (<https://www.kanakinfosystems.com>).

from odoo import models, fields


class BookCategory(models.Model):
    _name = "book.category"
    _description = "Book Category"

    name = fields.Char(string="Category Name")
