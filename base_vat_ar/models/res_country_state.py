from odoo import models, fields, api


class ResCountryState(models.Model):

    _inherit = 'res.country.state'
    #check for repeated state names, based on the country name; avoiding repeated values (name,zip_code) for each country
    _sql_constraints = [('unique_state_name','UNIQUE (country_id,name)','Repeated state name. Please check the states list.')]
