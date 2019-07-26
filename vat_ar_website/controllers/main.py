##############################################################################
#   Copyright (c) 2018 Eynes/E-MIPS (www.eynes.com.ar)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
##############################################################################

import logging
from werkzeug.exceptions import Forbidden

from odoo import http, tools, _
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale


_logger = logging.getLogger(__name__)


class WebsiteSaleVatAr(WebsiteSale):

    def checkout_form_validate(self, mode, all_form_values, data):
        # mode: tuple ('new|edit', 'billing|shipping')
        # all_form_values: all values before preprocess
        # data: values after preprocess
        error = dict()
        error_message = []

        # Required fields from form
        required_fields = [f for f in (
            all_form_values.get('field_required') or '').split(',') if f]
        # Required fields from mandatory field function
        required_fields += mode[1] == 'shipping' and \
            self._get_mandatory_shipping_fields() or \
            self._get_mandatory_billing_fields()
        # Check if state required
        country = request.env['res.country']
        if data.get('country_id'):
            country = country.browse(int(data.get('country_id')))
            if 'state_code' in country.get_address_fields() and \
                    country.state_ids:
                required_fields += ['state_id']

        # error message for empty required fields
        for field_name in required_fields:
            if not data.get(field_name):
                error[field_name] = 'missing'

        # email validation
        if data.get('email') and not tools.single_email_re.match(
                data.get('email')):
            error["email"] = 'error'
            error_message.append(
                _('Invalid Email! Please enter a valid email address.'))

        # vat validation
        Partner = request.env['res.partner']
        if data.get("vat") and hasattr(Partner, "check_vat"):
            if data.get("country_id"):
                data["vat"] = Partner.fix_eu_vat_number(
                    data.get("country_id"), data.get("vat"))
            Partner.new({
                'vat': data['vat'],
                'document_type_id': (int(data['document_type_id'])
                                     if data.get('document_type_id')
                                     else False),
                'country_id': (int(data['country_id'])
                               if data.get('country_id') else False),
            })
            # try:
            #     partner_dummy.check_vat()
            # except ValidationError as e:
            #     error["vat"] = 'error0'
            #     error_message.append(str(e.args[0]))
            # try:
            #     partner_dummy.check_vat_string(data)
            # except ValidationError as e:
            #     error["vat"] = 'error0'
            #     error_message.append(str(e.args[0]))

        if [err for err in error.items() if err == 'missing']:
            error_message.append(_('Some required fields are empty.'))

        return error, error_message

    def _checkout_form_save(self, mode, checkout, all_values):
        Partner = request.env['res.partner']
        if mode[0] == 'new':
            partner_id = Partner.with_context(
                {'from_website': True}).sudo().create(checkout).id
        elif mode[0] == 'edit':
            partner_id = int(all_values.get('partner_id', 0))
            if partner_id:
                # double check
                order = request.website.sale_get_order()
                shippings = Partner.sudo().search([
                    ("id", "child_of",
                     order.partner_id.commercial_partner_id.ids)])
                if partner_id not in shippings.mapped('id') and \
                        partner_id != order.partner_id.id:
                    return Forbidden()
                Partner.browse(partner_id).sudo().write(checkout)
        return partner_id

    @http.route(['/shop/address'], type='http', methods=['GET', 'POST'],
                auth="public", website=True)
    def address(self, **kw):
        Partner = request.env['res.partner'].with_context(
            show_address=1).sudo()
        order = request.website.sale_get_order()

        redirection = self.checkout_redirection(order)
        if redirection:
            return redirection

        mode = (False, False)
        def_country_id = order.partner_id.country_id
        def_document_type_id = order.partner_id.document_type_id
        values, errors = {}, {}

        partner_id = int(kw.get('partner_id', -1))

        # IF PUBLIC ORDER
        if order.partner_id.id == request.website.user_id.sudo().partner_id.id:
            mode = ('new', 'billing')
            country_code = request.session['geoip'].get('country_code')
            if country_code:
                def_country_id = request.env['res.country'].search(
                    [('code', '=', country_code)], limit=1)
            else:
                def_country_id = request.website.user_id.sudo().country_id
        # IF ORDER LINKED TO A PARTNER
        else:
            if partner_id > 0:
                if partner_id == order.partner_id.id:
                    mode = ('edit', 'billing')
                else:
                    shippings = Partner.search([
                        ('id', 'child_of',
                         order.partner_id.commercial_partner_id.ids)])
                    if partner_id in shippings.mapped('id'):
                        mode = ('edit', 'shipping')
                    else:
                        return Forbidden()
                if mode:
                    values = Partner.browse(partner_id)
            elif partner_id == -1:
                mode = ('new', 'shipping')
            else:  # no mode - refresh without post?
                return request.redirect('/shop/checkout')

        # IF POSTED
        if 'submitted' in kw:
            pre_values = self.values_preprocess(order, mode, kw)
            errors, error_msg = self.checkout_form_validate(
                mode, kw, pre_values)
            post, errors, error_msg = self.values_postprocess(
                order, mode, pre_values, errors, error_msg)

            if errors:
                errors['error_message'] = error_msg
                values = kw
            else:
                partner_id = self._checkout_form_save(mode, post, kw)

                if mode[1] == 'billing':
                    order.partner_id = partner_id
                    order.onchange_partner_id()
                elif mode[1] == 'shipping':
                    order.partner_shipping_id = partner_id

                order.message_partner_ids = [
                    (4, partner_id), (3, request.website.partner_id.id)]
                if not errors:
                    return request.redirect(
                        kw.get('callback') or '/shop/checkout')

        country = 'country_id' in values and values['country_id'] != '' \
            and request.env['res.country'].browse(int(values['country_id']))
        country = country and country.exists() or def_country_id
        document = 'document_type_id' in values and \
            values['document_type_id'] != '' and \
            request.env['res.document.type'].browse(
                int(values['document_type_id']))
        document = document and document.exists() or def_document_type_id
        render_values = {
            'document': document,
            'documents': document.get_website_sale_documents(mode=mode[1]),
            'website_sale_order': order,
            'partner_id': partner_id,
            'mode': mode,
            'checkout': values,
            'country': country,
            'countries': country.get_website_sale_countries(mode=mode[1]),
            "states": country.get_website_sale_states(mode=mode[1]),
            'error': errors,
            'callback': kw.get('callback'),
        }
        return request.render("website_sale.address", render_values)


# class WebsiteSalePartner(WebsiteSale):
#
#     @http.route(['/shop/address'], type='http', methods=['GET', 'POST'],
#                 auth="public", website=True)
#     def address(self, **kw):
#         Partner = request.env['res.partner'].with_context(
#             show_address=1).sudo()
#         order = request.website.sale_get_order()
#
#         redirection = self.checkout_redirection(order)
#         if redirection:
#             return redirection
#
#         mode = (False, False)
#         def_country_id = order.partner_id.country_id
#         def_document_type_id = order.partner_id.document_type_id
#         values, errors = {}, {}
#
#         partner_id = int(kw.get('partner_id', -1))
#
#         # IF PUBLIC ORDER
#         if order.partner_id.id == request.website.user_id.sudo().partner_id.id:  # noqa
#             mode = ('new', 'billing')
#             country_code = request.session['geoip'].get('country_code')
#             if country_code:
#                 def_country_id = request.env['res.country'].search(
#                     [('code', '=', country_code)], limit=1)
#             else:
#                 def_country_id = request.website.user_id.sudo().country_id
#         # IF ORDER LINKED TO A PARTNER
#         else:
#             if partner_id > 0:
#                 if partner_id == order.partner_id.id:
#                     mode = ('edit', 'billing')
#                 else:
#                     shippings = Partner.search(
#                         [('id', 'child_of',
#                           order.partner_id.commercial_partner_id.ids)])
#                     if partner_id in shippings.mapped('id'):
#                         mode = ('edit', 'shipping')
#                     else:
#                         return Forbidden()
#                 if mode:
#                     values = Partner.browse(partner_id)
#             elif partner_id == -1:
#                 mode = ('new', 'shipping')
#             else:  # no mode - refresh without post?
#                 return request.redirect('/shop/checkout')
#
#         # IF POSTED
#         if 'submitted' in kw:
#             pre_values = self.values_preprocess(order, mode, kw)
#             errors, error_msg = self.checkout_form_validate(
#                 mode, kw, pre_values)
#             post, errors, error_msg = self.values_postprocess(
#                 order, mode, pre_values, errors, error_msg)
#
#             if errors:
#                 errors['error_message'] = error_msg
#                 values = kw
#             else:
#                 partner_id = self._checkout_form_save(mode, post, kw)
#
#                 if mode[1] == 'billing':
#                     order.partner_id = partner_id
#                     order.onchange_partner_id()
#                 elif mode[1] == 'shipping':
#                     order.partner_shipping_id = partner_id
#
#                 order.message_partner_ids = [
#                     (4, partner_id), (3, request.website.partner_id.id)]
#                 if not errors:
#                     return request.redirect(
#                         kw.get('callback') or '/shop/checkout')
#
#         country = 'country_id' in values and values['country_id'] != '' \
#             and request.env['res.country'].browse(int(values['country_id']))
#         country = country and country.exists() or def_country_id
#         document = 'document_type_id' in values and \
#             values['document_type_id'] != '' and \
#             request.env['res.document.type'].browse(
#                 int(values['document_type_id']))
#         document = document and document.exists() or def_document_type_id
#         render_values = {
#             'document': document,
#             'documents': document.get_website_sale_documents(mode=mode[1]),
#             'website_sale_order': order,
#             'partner_id': partner_id,
#             'mode': mode,
#             'checkout': values,
#             'country': country,
#             'countries': country.get_website_sale_countries(mode=mode[1]),
#             "states": country.get_website_sale_states(mode=mode[1]),
#             'error': errors,
#             'callback': kw.get('callback'),
#         }
#         return request.render("website_sale.address", render_values)
