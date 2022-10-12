from odoo import models, fields, api, _
from math import sin, cos, sqrt, atan2, radians
import uuid


class DeliveryControl(models.Model):
    _name = "delivery.control"
    _description = "Delivery Control"
    _inherit = ["mail.thread", "mail.activity.mixin", "portal.mixin"]

    name = fields.Char(default=_('New'))
    sale_order_id = fields.Many2one("sale.order", copy=False, readonly=True)
    stock_picking_id = fields.Many2one(
        "stock.picking", readonly=True, copy=False)
    account_move_id = fields.Many2one(
        "account.move", readonly=True, copy=False)
    partner_id = fields.Many2one("res.partner", string="Delivery Boy",
                                 domain="[('is_delivery_boy', '=',True), ('active_state', '=', 'online'),'|', ('company_id', '=', False),('company_id', '=', company_id)]")
    broadcasted_order = fields.Boolean()
    assigned_date = fields.Date(tracking=True)
    assigned = fields.Boolean()
    total_distance = fields.Float(
        string="Distance (KM)", compute="_compute_total_distance")
    customer_id = fields.Many2one("res.partner", string="Customer",
                                  domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    portal_view_url = fields.Char(compute="_compute_portal_view_url")

    def _compute_portal_view_url(self):
        for delivery in self:
            base_url = self.env['ir.config_parameter'].sudo(
            ).get_param('web.base.url')
            url = base_url + '/acceptance/order/' + str(delivery.id)
            delivery.portal_view_url = url

    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting_for_accept', 'Waiting for Acceptance'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('picked', 'Picked'),
        ('paid', 'Paid'),
        ('delivered', 'Delivered')], tracking=True, default="draft")
    delivered_date = fields.Date()
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company)
    user_id = fields.Many2one(
        "res.users", default=lambda self: self.env.user)
    access_token = fields.Char()
    notes = fields.Text()

    @api.model
    def create(self, vals):
        res = super(DeliveryControl, self).create(vals)
        res['name'] = self.env['ir.sequence'].next_by_code(
            'delivery.control') or _('New')
        res['access_token'] = uuid.uuid4().hex
        return res

    def action_accept(self):
        self.state = 'accepted'

    def action_reject(self):
        self.state = 'rejected'

    def action_picked(self):
        self.state = 'picked'

    def _delivery_mail_for_acceptance(self):
        ctx = {
            'email_to': self.partner_id.email,
            'email_from': self.user_id.partner_id.email,
            'send_mail': True,
            'record': self,
        }
        template = self.env.ref(
            "delivery_boy_knk.delivery_boy_acceptance_temp")
        template.with_context(ctx).send_mail(
            self.id, force_send=True, raise_exception=True)

    def _get_message(self, record):
        message = _("""<p style="margin: 0px; padding: 0px; font-size: 13px;">Dear, %(partner)s <br /><br />
                    A new delivery order <strong>%(name)s</strong>, has assigned to you.
                    <br />
                    <br/>
                    <a href=%(portal_view_url)s style="background-color: #875A7B; padding: 8px 16px 8px 16px; text-decoration: none; color: #fff; border-radius: 5px; font-size:13px;">
                        View Order
                    </a>
                    <br/>
                    <br />
                    Do not hesitate to contact us if you have any questions.
                    <br /><br />
                    Best Regards,
                    <br />
                    Thank you,
                    <br />
                    %(user)s""",
                    partner=record.partner_id.name,
                    name=record.name,
                    portal_view_url=record.portal_view_url,
                    user=record.user_id.name)
        return message

    def action_send_to_delivery_boy(self):
        if self.partner_id:
            self.assigned_date = fields.Date.today()
            self.assigned = True
            self.state = 'waiting_for_accept'
            self._delivery_mail_for_acceptance()
            body = self._get_message(self)
            self.message_post(body=body)

    @api.depends(
        'customer_id',
        'customer_id.street',
        'customer_id.zip',
        'customer_id.country_id',
        'customer_id.state_id',
        'customer_id.city',
        'company_id',
        'company_id.street',
        'company_id.zip',
        'company_id.country_id',
        'company_id.state_id',
        'company_id.city',)
    def _compute_total_distance(self):
        for deliver in self.filtered(lambda x: x.partner_id not in [None, False]):
            if not deliver.customer_id.partner_latitude and not deliver.customer_id.partner_longitude and deliver.customer_id:
                deliver.customer_id.geo_localize()
            if not deliver.company_id.company_latitude and not deliver.company_id.company_longitude and deliver.customer_id:
                deliver.company_id.geo_localize()
            R = 6373.0
            clat = radians(deliver.company_id.company_latitude)
            clon = radians(deliver.company_id.company_longitude)
            plat = radians(deliver.customer_id.partner_latitude)
            plon = radians(deliver.customer_id.partner_longitude)
            if clat and clon and plat and plon:
                dlon = clon - plon
                dlat = clat - plat

                a = sin(dlat / 2)**2 + cos(clat) * cos(plat) * sin(dlon / 2)**2
                c = 2 * atan2(sqrt(a), sqrt(1 - a))

                distance = R * c
                print(distance, '\n\n')
                deliver.total_distance = distance
            else:
                deliver.total_distance = 0.0
