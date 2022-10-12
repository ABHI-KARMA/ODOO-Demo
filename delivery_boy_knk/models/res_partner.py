from odoo import models, fields, api


class ResPartners(models.Model):
    _inherit = "res.partner"

    is_delivery_boy = fields.Boolean(
        string="Delivery Boy")
    active_state = fields.Selection([
        ('online', 'Online'),
        ('offline', 'Offline')], default="offline")

    def switch_to_online(self):
        self.active_state = 'online'

    def switch_to_offline(self):
        self.active_state = 'offline'


# class ResUsers(models.Model):
#     _inherit = "res.users"

#     is_delivery_boy = fields.Boolean(string="Delivery Boy")

#     @api.model_create_multi
#     def create(self, vals_list):
#         users = super(ResUsers, self).create(vals_list)
#         for user in users:
#             user.partner_id.is_delivery_boy = user.is_delivery_boy
#         return users
