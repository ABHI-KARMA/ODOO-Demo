# from odoo import models, fields


# class Website(models.Model):
#   _inherit = "website"

#   def _get_pricelist_available(self, req, show_visible=False):
#           """ Return the list of pricelists that can be used on website for the current user.
#           Country restrictions will be detected with GeoIP (if installed).
#           :param bool show_visible: if True, we don't display pricelist where selectable is False (Eg: Code promo)
#           :returns: pricelist recordset
#           """
#           website = ir_http.get_request_website()
#           if not website:
#               if self.env.context.get('website_id'):
#                   website = self.browse(self.env.context['website_id'])
#               else:
#                   # In the weird case we are coming from the backend (https://github.com/odoo/odoo/issues/20245)
#                   website = len(self) == 1 and self or self.search([], limit=1)
#           # isocountry = req and req.session.geoip and req.session.geoip.get(
#           #     'country_code') or False
#           partner = self.env.user.partner_id
#           pricelists = website._get_pl_partner_order(isocountry, show_visible,
#                                                      website.user_id.sudo().partner_id.property_product_pricelist.id,
#                                                      req and req.session.get(
#                                                          'website_sale_current_pl') or None,
#                                                      website.pricelist_ids,
#                                                      partner_pl=partner_pl and partner_pl.id or None,
#                                                      order_pl=last_order_pl and last_order_pl.id or None)
#           return self.env['product.pricelist'].browse(pricelists)

#     def get_pricelist_available(self, show_visible=False):
#       return self._get_pricelist_available(request, show_visible)
