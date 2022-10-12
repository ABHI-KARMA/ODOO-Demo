# -*- coding: utf-8 -*-
# Powered by Kanak Infosystems LLP.
# © 2020 Kanak Infosystems LLP. (<https://www.kanakinfosystems.com>).

from odoo import http, fields
from odoo.http import request
from odoo.addons.website.controllers.main import QueryURL
from odoo.osv import expression


class TableCompute(object):

    def __init__(self):
        self.table = {}

    def _check_place(self, posx, posy, sizex, sizey, ppr):
        res = True
        for y in range(sizey):
            for x in range(sizex):
                if posx + x >= ppr:
                    res = False
                    break
                row = self.table.setdefault(posy + y, {})
                if row.setdefault(posx + x) is not None:
                    res = False
                    break
            for x in range(ppr):
                self.table[posy + y].setdefault(x, None)
        return res

    def process(self, products, ppg=20, ppr=4):
        # Compute products positions on the grid
        minpos = 0
        index = 0
        maxy = 0
        x = 0
        for p in products:
            x = min(max(p.website_size_x, 1), ppr)
            y = min(max(p.website_size_y, 1), ppr)
            if index >= ppg:
                x = y = 1

            pos = minpos
            while not self._check_place(pos % ppr, pos // ppr, x, y, ppr):
                pos += 1
            # if 21st products (index 20) and the last line is full (ppr products in it), break
            # (pos + 1.0) / ppr is the line where the product would be inserted
            # maxy is the number of existing lines
            # + 1.0 is because pos begins at 0, thus pos 20 is actually the 21st block
            # and to force python to not round the division operation
            if index >= ppg and ((pos + 1.0) // ppr) > maxy:
                break

            if x == 1 and y == 1:   # simple heuristic for CPU optimization
                minpos = pos // ppr

            for y2 in range(y):
                for x2 in range(x):
                    self.table[(pos // ppr) + y2][(pos % ppr) + x2] = False
            self.table[pos // ppr][pos % ppr] = {
                'product': p, 'x': x, 'y': y,
                'ribbon': p.website_ribbon_id,
            }
            if index <= ppg:
                maxy = max(maxy, y + (pos // ppr))
            index += 1

        # Format table according to HTML needs
        rows = sorted(self.table.items())
        rows = [r[1] for r in rows]
        for col in range(len(rows)):
            cols = sorted(rows[col].items())
            x += len(cols)
            rows[col] = [r[1] for r in cols if r[1]]

        return rows


class Library(http.Controller):

    def _get_pricelist_context(self):
        pricelist_context = dict(request.env.context)
        pricelist = False
        if not pricelist_context.get('pricelist'):
            pricelist = request.website.get_current_pricelist()
            pricelist_context['pricelist'] = pricelist.id
        else:
            pricelist = request.env['product.pricelist'].browse(
                pricelist_context['pricelist'])

        return pricelist_context, pricelist

    def _get_search_order(self, post):
        order = post.get('order')
        if order == 'available':
            return [('qty_available', '!=', 0.0)]
        elif order == 'not_available':
            return [('qty_available', '=', 0.0)]
        else:
            return []

    def _get_search_domain(self, search, category, attrib_values, search_in_description=True):
        domains = [request.website.sale_product_domain()]
        if search:
            for srch in search.split(" "):
                subdomains = [
                    [('name', 'ilike', srch)],
                    [('product_variant_ids.default_code', 'ilike', srch)]
                ]
                if search_in_description:
                    subdomains.append([('description', 'ilike', srch)])
                    subdomains.append([('description_sale', 'ilike', srch)])
                domains.append(expression.OR(subdomains))

        if category:
            domains.append([('public_categ_ids', 'child_of', int(category))])

        if attrib_values:
            attrib = None
            ids = []
            for value in attrib_values:
                if not attrib:
                    attrib = value[0]
                    ids.append(value[1])
                elif value[0] == attrib:
                    ids.append(value[1])
                else:
                    domains.append(
                        [('attribute_line_ids.value_ids', 'in', ids)])
                    attrib = value[0]
                    ids = [value[1]]
            if attrib:
                domains.append([('attribute_line_ids.value_ids', 'in', ids)])

        return expression.AND(domains)

    def sitemap_shop(env, rule, qs):
        if not qs or qs.lower() in '/library':
            yield {'loc': '/library'}
        Category = request.env['product.public.category']
        dom = sitemap_qs2dom(qs, '/library/category', Category._rec_name)
        dom += env['website'].get_current_website().website_domain()
        for cat in Category.search(dom):
            loc = '/library/category/%s' % slug(cat)
            if not qs or qs.lower() in loc:
                yield {'loc': loc}

    @http.route([
        '''/library''',
        '''/library/page/<int:page>''',
        '''/library/category/<model("product.public.category"):category>''',
        '''/library/category/<model("product.public.category"):category>/page/<int:page>'''
    ], type='http', auth="user", website=True, sitemap=sitemap_shop)
    def library(self, page=0, category=None, search='', ppg=False, **post):
        add_qty = int(post.get('add_qty', 1))
        Category = request.env['product.public.category']
        if category:
            category = Category.search([('id', '=', int(category))], limit=1)
            if not category or not category.can_access_from_current_website():
                raise NotFound()
        else:
            category = Category

        if ppg:
            try:
                ppg = int(ppg)
                post['ppg'] = ppg
            except ValueError:
                ppg = False
        if not ppg:
            ppg = request.env['website'].get_current_website().shop_ppg or 20

        ppr = request.env['website'].get_current_website().shop_ppr or 4

        attrib_list = request.httprequest.args.getlist('attrib')
        attrib_values = [[int(x) for x in v.split("-")]
                         for v in attrib_list if v]
        attributes_ids = {v[0] for v in attrib_values}
        attrib_set = {v[1] for v in attrib_values}

        domain = self._get_search_domain(search, category, attrib_values)

        keep = QueryURL('/library', category=category and int(category),
                        search=search, attrib=attrib_list, order=post.get('order'))

        pricelist_context, pricelist = self._get_pricelist_context()

        request.context = dict(
            request.context, pricelist=pricelist.id, partner=request.env.user.partner_id)

        url = "/library"
        if search:
            post["search"] = search
        if attrib_list:
            post['attrib'] = attrib_list

        Product = request.env['product.template'].with_context(bin_size=True)
        domain += [('is_book', '=', True)]
        domain += self._get_search_order(post)
        search_product = Product.search(domain)
        website_domain = request.website.website_domain()
        # categs_domain = [('parent_id', '=', False)] + website_domain
        # if search:
        #     search_categories = Category.search(
        #         [('product_tmpl_ids', 'in', search_product.ids)] + website_domain).parents_and_self
        #     categs_domain.append(('id', 'in', search_categories.ids))
        # else:
        #     search_categories = Category
        # categs = Category.search(categs_domain)

        if category:
            url = "/library/category/%s" % slug(category)

        product_count = len(search_product)
        pager = request.website.pager(
            url=url, total=product_count, page=page, step=ppg, scope=7, url_args=post)
        offset = pager['offset']
        products = search_product[offset: offset + ppg]

        ProductAttribute = request.env['product.attribute']
        if products:
            # get all products without limit
            attributes = ProductAttribute.search(
                [('product_tmpl_ids', 'in', search_product.ids)])
        else:
            attributes = ProductAttribute.browse(attributes_ids)

        values = {
            'search': search,
            'category': category,
            'attrib_values': attrib_values,
            'attrib_set': attrib_set,
            'pager': pager,
            'pricelist': pricelist,
            'add_qty': add_qty,
            'products': products,
            'search_count': product_count,  # common for all searchbox
            'bins': TableCompute().process(products, ppg, ppr),
            'ppg': ppg,
            'ppr': ppr,
            'attributes': attributes,
            'keep': keep,
        }
        if category:
            values['main_object'] = category

        return request.render("library_management_system.library_management_products", values)

    @http.route(['/shop/<model("product.template"):product>', '/library/book/<model("product.template"):product>'],
                type='http', auth="public", website=True, sitemap=True)
    def product(self, product, category='', search='', **kwargs):
        if not product.can_access_from_current_website():
            raise NotFound()
        if product.is_book:
            return request.render("library_management_system.library_management_product", self._prepare_product_values(product, category, search, **kwargs))
        else:
            return request.render("website_sale.product", self._prepare_product_values(product, category, search, **kwargs))

    def _prepare_product_values(self, product, category, search, **kwargs):
        add_qty = int(kwargs.get('add_qty', 1))

        product_context = dict(request.env.context, quantity=add_qty,
                               active_id=product.id,
                               partner=request.env.user.partner_id)
        ProductCategory = request.env['product.public.category']

        if category:
            category = ProductCategory.browse(int(category)).exists()

        attrib_list = request.httprequest.args.getlist('attrib')
        attrib_values = [[int(x) for x in v.split("-")]
                         for v in attrib_list if v]
        attrib_set = {v[1] for v in attrib_values}

        keep = QueryURL('/library', category=category and category.id,
                        search=search, attrib=attrib_list)

        categs = ProductCategory.search([('parent_id', '=', False)])

        pricelist = request.website.get_current_pricelist()

        if not product_context.get('pricelist'):
            product_context['pricelist'] = pricelist.id
            product = product.with_context(product_context)

        # Needed to trigger the recently viewed product rpc
        view_track = request.website.viewref(
            "library_management_system.library_management_product").track

        return {
            'search': search,
            'category': category,
            'pricelist': pricelist,
            'attrib_values': attrib_values,
            'attrib_set': attrib_set,
            'keep': keep,
            'categories': categs,
            'main_object': product,
            'product': product,
            'add_qty': add_qty,
            'view_track': view_track,
        }

    def _send__request_mail(self, rec):
        ctx = {
            'email_to': rec.company_id.email,
            'email_from': rec.email,
            'send_mail': True,
            'name': rec.partner_id.name,
            'book_name': rec.product_id.name,
            'request_number': rec.name,
        }
        template = rec.env.ref(
            'library_management_system.email_template_for_issue_book_request')
        template.sudo().with_context(ctx).send_mail(
            rec.id, force_send=True, raise_exception=False)

    @http.route('/request_book', type="http", auth="user", website=True)
    def request_book(self, **post):
        print("\n\n record", post)
        if post.get('cid'):
            record = request.env['product.template'].browse(
                int(post.get('cid')))
            partner = request.env['res.partner'].search(
                [('name', '=', request.env.user.name)])
            if record:
                return request.render('library_management_system.book_issue_request_form', {'data': record, 'partner': partner.name, 'email': partner.email})
            else:
                print("record not found")

        if request.httprequest.method == 'POST':
            partner = request.env['res.partner'].search(
                [('name', '=', post.get('student_name'))])
            if partner:
                res_partner = partner
            else:
                res_partner = request.env['res.partner'].create(
                    {'name': post['student_name'], 'email': post.get('email')})
            values = {
                'partner_id': res_partner.id,
                'email': res_partner.email,
                'date': fields.Date.today(),
                'product_id': int(post.get('id')),
                'membership_id': res_partner.membership if res_partner.membership else "Not a Member",
                'membership_exp_date': res_partner.membership_exp_date if res_partner.membership_exp_date else None,
            }
            rec = request.env['book.request'].create(values)
            print(rec.product_id, '\n\n')
            self._send__request_mail(rec)
            return request.render('library_management_system.library_management_system_request_book', {'record': rec})

    def _send__reserve_mail(self, rec):
        ctx = {
            'email_to': rec.company_id.email,
            'email_from': rec.env.user.email,
            'send_mail': True,
            'name': rec.partner_id.name,
            'book_name': rec.book_ids.product_id.name,
            'request_number': rec.name,
        }
        template = rec.env.ref(
            'library_management_system.email_template_for_reserve_book')
        template.sudo().with_context(ctx).send_mail(
            rec.id, force_send=True, raise_exception=False)

    @http.route('/reserve_book', type="http", auth="user", website=True)
    def reserve_book(self, **post):
        if post.get('cid'):
            record = request.env['product.template'].browse(
                int(post.get('cid')))
            partner = request.env['res.partner'].search(
                [('name', '=', request.env.user.name)])
            if record:
                return request.render('library_management_system.book_issue_reservation_form', {'data': record, 'partner': partner.name, 'email': partner.email})
            else:
                print("record not found")

        if request.httprequest.method == 'POST':
            partner = request.env['res.partner'].search(
                [('name', '=', post.get('student_name'))])
            if partner:
                res_partner = partner[0]
            else:
                res_partner = request.env['res.partner'].create(
                    {'name': post['student_name'], 'email': post.get('email')})
            reservation_id = request.env['book.reservation.line'].create(
                {'product_id': request.env['product.template'].search([('id', '=', post.get('id'))]).id})
            values = {
                'partner_id': res_partner.id,
                'date': fields.Date.today(),
                'membership_id': res_partner.membership if res_partner.membership else "Not a Member",
                'membership_exp_date': res_partner.membership_exp_date if res_partner.membership_exp_date else None,
                'book_ids': reservation_id
            }
            rec = request.env['book.reservation'].create(values)
            self._send__reserve_mail(rec)
            return request.render('library_management_system.library_management_system_reservation_book', {'record': rec})
