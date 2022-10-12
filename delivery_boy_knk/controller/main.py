# -*- coding: utf-8 -*-
# Powered by Kanak Infosystems LLP.
# © 2020 Kanak Infosystems LLP. (<https://www.kanakinfosystems.com>).

from odoo import http, fields, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager, get_records_pager


class CustomerPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id

        DeliveredOrders = request.env['delivery.control'].sudo()

        if 'delivered_orders' in counters:
            values['delivered_orders'] = DeliveredOrders.search_count([('partner_id', '=', partner.id), ('state', '=', 'delivered')]) \
                if DeliveredOrders.check_access_rights('read', raise_exception=False) else 0

        return values

    @http.route([
        '/my/successful/delivered_orders',
        '/my/successful/delivered_orders/<int:page>'],
        type='http', auth="user", website=True)
    def portal_my_issued(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        DeliveredOrders = request.env['delivery.control'].sudo()
        domain = [('partner_id', '=', partner.id), ('state', '=', 'delivered')]

        searchbar_sortings = {
            'date': {'label': _('Delivered Date'), 'order': 'delivered_date'},
            'name': {'label': _('Reference'), 'order': 'name'},
        }

        # default sortby order
        if not sortby:
            sortby = 'date'
        sort_order = searchbar_sortings[sortby]['order']

        if date_begin and date_end:
            domain += [('create_date', '>=', date_begin),
                       ('create_date', '<=', date_end)]

        # count for pager
        delivered_count = DeliveredOrders.search_count(domain)
        # make pager
        pager = portal_pager(
            url="/my/successful/delivered_orders",
            url_args={'date_begin': date_begin,
                      'date_end': date_end, 'sortby': sortby},
            total=delivered_count,
            page=page,
            step=self._items_per_page
        )
        # search the count to display, according to the pager data
        delivered_records = DeliveredOrders.search(
            domain, order=sort_order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_delivered_history'] = delivered_records.ids[:100]

        values.update({
            'date': date_begin,
            'delivered_records': delivered_records.sudo(),
            'page_name': 'delivered_records',
            'pager': pager,
            'default_url': '/my/successful/delivered_orders',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
        })
        return request.render("delivery_boy_knk.portal_my_successful_delivered_record", values)

    @http.route([
        '/broadcasted/delivery/orders',
        '/broadcasted/delivery/orders/<int:page>'],
        type='http', auth="user", website=True)
    def get_broadcasted_orders(self, page=1, **kw):
        values = self._prepare_portal_layout_values()
        delivery_obj = request.env['delivery.control'].sudo()

        if kw.get('order_id'):
            order = delivery_obj.search([('id', '=', kw.get('order_id'))])
            return request.render('delivery_boy_knk.delivery_order_details_form', {'order': order})

        domain = [('broadcasted_order', '=', True),
                  ('state', 'in', ['draft', 'rejected'])]
        delivery_brd_count = delivery_obj.search_count(domain)
        delivery_brd_orders = delivery_obj.search(domain)

        pager = portal_pager(
            url="/broadcasted/delivery/orders",
            total=delivery_brd_count,
            page=page,
            step=self._items_per_page
        )

        delivery_brd_orders = delivery_obj.search(
            domain, limit=self._items_per_page, offset=pager['offset'])
        request.session['broadcasted_order_history'] = delivery_brd_orders.ids[:100]

        values.update({
            'delivery_brd_orders': delivery_brd_orders.sudo(),
            'page_name': 'delivery_brd_orders',
            'pager': pager,
            'default_url': '/broadcasted/delivery/orders',
        })

        return request.render("delivery_boy_knk.delivery_control_broadcasted_orders", values)

    @http.route([
        '/broadcasted/delivery/<int:order_id>'
    ], type='http', auth="user", website=True)
    def broadcasted_order_details(self, **post):
        delivery_obj = request.env['delivery.control'].sudo()
        if post.get('order_id'):
            delivery_package = delivery_obj.search(
                [('id', '=', int(post.get('order_id')))])
            return request.render('delivery_boy_knk.delivery_order_details_form', {'order_details': delivery_package})

    @http.route([
        '/delivery/assign/<int:id>'],
        type='http', auth="user", website=True)
    def delivery_assigntome(self, **post):
        delivery_obj = request.env['delivery.control'].sudo()
        partner = request.env.user.partner_id
        if post.get('id') and partner:
            delivery_package = delivery_obj.search(
                [('id', '=', int(post.get('id')))])
            delivery_package.write({
                'partner_id': partner.id,
                'state': 'accepted',
                'assigned_date': fields.Date.today()
            })

            return request.redirect('/broadcasted/delivery/orders')

    @http.route([
        '/todo/delivery/orders'
    ], type="http", auth="user", website=True)
    def to_do_delivery_orders(self, **kw):
        delivery_obj = request.env['delivery.control'].sudo()
        domain = [('partner_id', '=', request.env.user.partner_id.id)]
        to_do_orders = delivery_obj.search(domain)
        return request.render('delivery_boy_knk.delivery_control_to_do_deliveries', {'orders': to_do_orders})

    @http.route([
        '/acceptance/order/<int:order_id>'], type="http", auth="user", website=True)
    def delivery_boy_acceptance_order(self, **kw):
        delivery_obj = request.env['delivery.control'].sudo()
        domain = [('id', '=', int(kw.get('order_id')))]
        record = delivery_obj.search(domain)
        return request.render('delivery_boy_knk.delivery_order_acceptance_template', {'record': record})

    @http.route('/accept/order/<int:order_id>', type="http", auth="user", website=True)
    def accept_order(self, **kw):
        delivery_obj = request.env['delivery.control'].sudo()
        domain = [('id', '=', int(kw.get('order_id')))]
        record = delivery_obj.search(domain)
        record.write({'state': 'accepted'})
        return request.render('delivery_boy_knk.delivery_order_acceptance_template', {'record': record})

    @http.route('/reject/order/<int:order_id>', type="http", auth="user", website=True)
    def reject_order(self, **kw):
        delivery_obj = request.env['delivery.control'].sudo()
        domain = [('id', '=', int(kw.get('order_id')))]
        record = delivery_obj.search(domain)
        record.write({'state': 'rejected', 'partner_id': False,'assigned':False})
        return request.redirect('/todo/delivery/orders')


# import json, urllib
# from urllib import urlencode
# import googlemaps
# start = "Bridgewater, Sa, Australia"
# finish = "Stirling, SA, Australia"

# url = 'http://maps.googleapis.com/maps/api/directions/json?%s' % urlencode((
#             ('origin', start),
#             ('destination', finish)
#  ))
# ur = urllib.urlopen(url)
# result = json.load(ur)

# for i in range (0, len (result['routes'][0]['legs'][0]['steps'])):
#     j = result['routes'][0]['legs'][0]['steps'][i]['html_instructions']
#     print j
