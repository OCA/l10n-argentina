# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2012-2014 E-MIPS (http://www.e-mips.com.ar)
#    Copyright (c) 2014 Aconcagua Team (http://www.proyectoaconcagua.com.ar)
#    All Rights Reserved. See AUTHORS for details.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import osv, fields
from openerp.tools.translate import _
 
__author__ = "Sebastian Kennedy <skennedy@e-mips.com.ar>, Anibal Alejandro Guanca <aguanca@e-mips.com.ar>"

class res_document_type(osv.osv):
    _name = 'res.document.type'
    _description = 'Document type'

    _columns = {
        'name': fields.char('Document type', size=40),
        'afip_code': fields.char('Afip code', size=10),
        'verification_required': fields.boolean('Verification required'),
    }

    _defaults = {
        'verification_required': lambda *a: False,
        }

res_document_type()
	
class res_partner(osv.osv):
    _inherit = 'res.partner'
    
    _columns = {
		'document_type_id': fields.many2one('res.document.type', 'Document type'),
	}

    def check_vat(self, cr, uid, ids, context=None):
        '''
        Check the VAT number depending of the country.
        http://sima-pc.com/nif.php
        '''
        for partner in self.browse(cr, uid, ids, context=context):
            if not partner.vat:
                continue
            if partner.country_id:
                vat_country = partner.country_id.code.lower()
                vat_number = partner.vat
            else:
                vat_country, vat_number = partner.vat[:2].lower(), partner.vat[2:].replace(' ', '')
            if partner.document_type_id:
                if partner.document_type_id.verification_required:
                    if not hasattr(self, 'check_vat_' + vat_country):
                        return True
                    check = getattr(self, 'check_vat_' + vat_country)
                    if not check(vat_number):
                        return False
                else:
                    return True

            else:
                if not hasattr(self, 'check_vat_' + vat_country):
                    return True

                check = getattr(self, 'check_vat_' + vat_country)
                if not check(vat_number):
                    return False
        return True

    _constraints = [(check_vat, _('The Vat does not seems to be correct.'), ["vat"])]

    def check_vat_ar(self,vat):
        """
        Check VAT Routine for Argentina.
        """
        if len(vat) != 11: return False
        try: 
            int(vat)
        except ValueError:
            return False

        l=[5,4,3,2,7,6,5,4,3,2]

        var1=0
        for i in range(10):
            var1=var1+int(vat[i])*l[i]
        var3=11-var1%11

        if var3==11: var3=0
        if var3==10: var3=9
        if var3 == int(vat[10]):

            return True

        return False    

res_partner()
