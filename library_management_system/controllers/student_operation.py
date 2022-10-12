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

        IssueOrder = request.env['book.issue']
        RequestOrder = request.env['book.request']
        ReservationOrder = request.env['book.reservation']

        if 'request_count' in counters:
            values['request_count'] = RequestOrder.search_count([('partner_id', '=', partner.id)]) \
                if RequestOrder.check_access_rights('read', raise_exception=False) else 0
        if 'reservation_count' in counters:
            values['reservation_count'] = ReservationOrder.search_count([('partner_id', '=', partner.id)]) \
                if ReservationOrder.check_access_rights('read', raise_exception=False) else 0
        if 'issue_count' in counters:
            values['issue_count'] = IssueOrder.search_count([('partner_id', '=', partner.id)]) \
                if IssueOrder.check_access_rights('read', raise_exception=False) else 0

        return values

    @http.route(['/requests'], type="http", auth="public", website=True)
    def requests(self):
        records = request.env['book.request'].search(
            [('partner_id', '=', request.env.user.partner_id.id)])
        return request.render(
            'library_management_system.issues_requests',
            {'records': records})

    @http.route('/reservations', type="http", auth="public", website=True)
    def reservations(self):
        records = request.env['book.reservation'].search(
            [('partner_id', '=', request.env.user.partner_id.id)])
        return request.render(
            'library_management_system.book_reservations',
            {'records': records})

    @http.route(['/issued'], type="http", auth="public", website=True)
    def issued(self):
        records = request.env['book.issue'].search(
            [('partner_id', '=', request.env.user.partner_id.id)])
        return request.render(
            'library_management_system.issued_records',
            {'records': records})

    @http.route(['/my/requests', '/my/requests/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_requests(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        RequestOrder = request.env['book.request']

        domain = [('partner_id', '=', partner.id)]

        searchbar_sortings = {
            'date': {'label': _('Request Date'), 'order': 'date desc'},
            'name': {'label': _('Reference'), 'order': 'name'},
            'stage': {'label': _('Stage'), 'order': 'state'},
        }

        # default sortby order
        if not sortby:
            sortby = 'date'
        sort_order = searchbar_sortings[sortby]['order']

        if date_begin and date_end:
            domain += [('create_date', '>', date_begin),
                       ('create_date', '<=', date_end)]

        # count for pager
        request_count = RequestOrder.search_count(domain)
        # make pager
        pager = portal_pager(
            url="/my/requests",
            url_args={'date_begin': date_begin,
                      'date_end': date_end, 'sortby': sortby},
            total=request_count,
            page=page,
            step=self._items_per_page
        )
        # search the count to display, according to the pager data
        requests = RequestOrder.search(
            domain, order=sort_order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_requests_history'] = requests.ids[:100]

        values.update({
            'date': date_begin,
            'requests': requests.sudo(),
            'page_name': 'request',
            'pager': pager,
            'default_url': '/my/requests',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
        })
        return request.render("library_management_system.portal_my_requests", values)

    @http.route(['/my/reservations', '/my/reservations/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_reservations(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        ReservationOrder = request.env['book.reservation']

        domain = [('partner_id', '=', partner.id)]

        searchbar_sortings = {
            'date': {'label': _('Request Date'), 'order': 'date desc'},
            'name': {'label': _('Reference'), 'order': 'name'},
            'stage': {'label': _('Stage'), 'order': 'state'},
        }

        # default sortby order
        if not sortby:
            sortby = 'date'
        sort_order = searchbar_sortings[sortby]['order']

        if date_begin and date_end:
            domain += [('create_date', '>', date_begin),
                       ('create_date', '<=', date_end)]

        # count for pager
        reservation_count = ReservationOrder.search_count(domain)
        # make pager
        pager = portal_pager(
            url="/my/reservations",
            url_args={'date_begin': date_begin,
                      'date_end': date_end, 'sortby': sortby},
            total=reservation_count,
            page=page,
            step=self._items_per_page
        )
        # search the count to display, according to the pager data
        reservations = ReservationOrder.search(
            domain, order=sort_order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_reservations_history'] = reservations.ids[:100]

        values.update({
            'date': date_begin,
            'reservations': reservations.sudo(),
            'page_name': 'reservation',
            'pager': pager,
            'default_url': '/my/reservations',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
        })
        return request.render("library_management_system.portal_my_reservations", values)

    @http.route(['/my/issued', '/my/issued/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_issued(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        IssueOrder = request.env['book.issue']
        domain = [('partner_id', '=', partner.id)]

        searchbar_sortings = {
            'date': {'label': _('Request Date'), 'order': 'issue_date desc'},
            'name': {'label': _('Reference'), 'order': 'name'},
            'stage': {'label': _('Stage'), 'order': 'state'},
        }

        # default sortby order
        if not sortby:
            sortby = 'date'
        sort_order = searchbar_sortings[sortby]['order']

        if date_begin and date_end:
            domain += [('create_date', '>', date_begin),
                       ('create_date', '<=', date_end)]

        # count for pager
        issue_count = IssueOrder.search_count(domain)
        print(issue_count, '\n\n')
        # make pager
        pager = portal_pager(
            url="/my/issued",
            url_args={'date_begin': date_begin,
                      'date_end': date_end, 'sortby': sortby},
            total=issue_count,
            page=page,
            step=self._items_per_page
        )
        # search the count to display, according to the pager data
        issue_records = IssueOrder.search(
            domain, order=sort_order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_issued_history'] = issue_records.ids[:100]

        values.update({
            'date': date_begin,
            'issued_records': issue_records.sudo(),
            'page_name': 'issued_records',
            'pager': pager,
            'default_url': '/my/issued',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
        })
        print(values, '\n\n')
        return request.render("library_management_system.portal_my_issued_records", values)
