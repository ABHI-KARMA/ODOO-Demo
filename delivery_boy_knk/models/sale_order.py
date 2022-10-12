from odoo import models, fields, _


class SaleOrder(models.Model):
    _inherit = "sale.order"

    # delivery_control_id = fields.Many2one("delivery.control")

    def _create_delivery_control(self):
        delivery_obj = self.env['delivery.control']
        values = {
            'sale_order_id': self.id,
            'stock_picking_id': self.picking_ids[0].id if self.picking_ids else False,
            'account_move_id': self.invoice_ids[0].id if self.invoice_ids else False,
            'customer_id': self.partner_id.id,
            'company_id': self.company_id.id,
        }
        delivery = delivery_obj.create(values)

    def action_confirm(self):
        self._create_delivery_control()
        return super(SaleOrder, self).action_confirm()

    def button_all_delivery_controls(self):
        values = {
            'name': _('Delivery Controls'),
            'res_model': 'delivery.control',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'domain': [('sale_order_id', '=', self.id)]
        }
        return values
