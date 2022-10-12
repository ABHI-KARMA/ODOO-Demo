from odoo import models, fields, api
from odoo.tools import config


class ResCompany(models.Model):
    _inherit = "res.company"

    date_localization = fields.Date(string='Geolocation Date')

    company_latitude = fields.Float()
    company_longitude = fields.Float()

    def write(self, vals):
        if any(field in vals for field in ['street', 'zip', 'city', 'state_id', 'country_id']) \
                and not all('company_%s' % field in vals for field in ['latitude', 'longitude']):
            vals.update({
                'company_latitude': 0.0,
                'company_longitude': 0.0,
            })
        return super(ResCompany, self).write(vals)

    @api.model
    def _geo_localize(self, street='', zip='', city='', state='', country=''):
        geo_obj = self.env['base.geocoder']
        search = geo_obj.geo_query_address(
            street=street, zip=zip, city=city, state=state, country=country)
        result = geo_obj.geo_find(search, force_country=country)
        if result is None:
            search = geo_obj.geo_query_address(
                city=city, state=state, country=country)
            result = geo_obj.geo_find(search, force_country=country)
        return result

    def geo_localize(self):
        # We need country names in English below
        if not self._context.get('force_geo_localize') \
                and (self._context.get('import_file')
                     or any(config[key] for key in ['test_enable', 'test_file', 'init', 'update'])):
            return False
        for company in self.with_context(lang='en_US'):
            result = self._geo_localize(company.street,
                                        company.zip,
                                        company.city,
                                        company.state_id.name,
                                        company.country_id.name)

            if result:
                company.write({
                    'company_latitude': result[0],
                    'company_longitude': result[1],
                    'date_localization': fields.Date.context_today(company)
                })
        return True
