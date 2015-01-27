# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2011-2013 Serpent Consulting Services (<http://www.serpentcs.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
############################################################################
import time

from openerp.report import report_sxw
import amount_to_text_sp
#~ import math
#~ 
#~ unites = {
    #~ 0: ' ', 1:'un', 2:'dos', 3:'tres', 4:'cuatro', 5:'cinco', 6:'seis', 7:'siete', 8:'ocho', 9:'nueve', 10:'diez',
    #~ 11:'once', 12:'doce', 13:'trece', 14:'catorce', 15:'quince', 16:'dieciseis', 17:'diecisiete', 18:'dieciocho', 19:'diecinueve', 20:'veinte',
    #~ 21:'veintiuno', 22:'veintidos', 23:'veintitres', 24:'veinticuatro', 25:'veinticinco', 26:'veintiseis', 27:'veintisiete', 28:'veintiocho', 29:'veintinueve'}
#~ 
#~ dizaine = {
    #~ 1: 'diez', 2:'veinte', 3:'treinta',4:'cuarenta', 5:'cincuenta', 6:'sesenta', 7:'setenta', 8:'ochenta', 9:'noventa'
#~ }
#~ 
#~ centaine = {
    #~ 0:'', 1: 'ciento', 2:'doscientos', 3:'trescientos',4:'cuatrocientos', 5:'quinientos', 6:'seiscientos', 7:'setecientos', 8:'ochocientos', 9:'novecientos'
#~ }
#~ 
#~ mille = {
    #~ 0:' ', 1:'mil'
#~ }
#~ 
#~ 
#~ def _100_to_text_sp(chiffre):
	#~ if chiffre in unites:
		#~ return unites[chiffre]
	#~ else:
		#~ if chiffre%10>0:
			#~ return dizaine[chiffre / 10]+' y '+unites[chiffre % 10]
		#~ else:
			#~ return dizaine[chiffre / 10]
#~ 
#~ def _1000_to_text_sp(chiffre):
	#~ d = _100_to_text_sp(chiffre % 100)
	#~ d2 = chiffre/100
	#~ if d2>0 and d:
		#~ return centaine[d2]+' '+d
	#~ elif d2>0 and not(d):
			#~ return 'cien'
	#~ elif d2>1 and not(d):
		#~ return centaine[d2]+'s'
	#~ else:
			#~ return centaine[d2] or d
#~ 
#~ def _10000_to_text_sp(chiffre):
	#~ if chiffre==0:
		#~ return 'cero'
	#~ part1 = _1000_to_text_sp(chiffre % 1000)
	#~ part2 = mille.get(chiffre / 1000,  _1000_to_text_sp(chiffre / 1000)+' mil')
	#~ if part2 and part1:
		#~ part1 = ' '+part1
	#~ return part2+part1
	
class order(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(order, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time, 
            'show_formas_de_pago':self._show_formas_de_pago,
            'show_comprobantes_cr':self._show_comprobantes_cr,
            'show_comprobantes_dr':self._show_comprobantes_dr,
            'show_cheques_propios':self._show_cheques_propios,
            'show_cheques_recibo_terceros':self._show_cheques_recibo_terceros,
            'show_cheques_terceros':self._show_cheques_terceros,
            'show_retenciones':self._show_retenciones,
            'amount_to_text_sp': amount_to_text_sp.amount_to_text_sp,
            'saldo': self._saldo,
        })

    def _show_formas_de_pago(self, uid, voucher_id, context=None):
        cr = self.cr
        cr.execute('select sum(amount) from payment_mode_receipt_line where voucher_id=%s',(voucher_id,))
        aux = cr.fetchone()
        return aux[0] or 0.0

    def _show_cheques_propios(self, uid, voucher_id, context=None):
        cr = self.cr
        cr.execute('select sum(amount) from account_issued_check where voucher_id=%s',(voucher_id,))
        aux = cr.fetchone()
        return aux[0] or 0.0

    def _show_cheques_recibo_terceros(self, uid, voucher_id, context=None):
        cr = self.cr
        cr.execute('select sum(amount) from account_third_check where source_voucher_id=%s',(voucher_id,))
        aux = cr.fetchone()
        return aux[0] or 0.0

    def _show_cheques_terceros(self, uid, voucher_id, context=None):
        cr = self.cr
        print voucher_id
        cr.execute('select sum(tc.amount) from third_check_voucher_rel tr, account_third_check tc \
                    where tr.third_check_id=tc.id and tr.dest_voucher_id=%s',(voucher_id,))
        aux = cr.fetchone()
        return aux[0] or 0.0
        
    def _show_comprobantes_cr(self, uid, voucher_id, context=None):
        cr = self.cr
        cr.execute('select sum(amount) from account_voucher_line where voucher_id=%s and type=%s',(voucher_id,'cr',))
        aux = cr.fetchone()
        return aux[0] or 0.0
        
    def _show_comprobantes_dr(self, uid, voucher_id, context=None):
        cr = self.cr
        cr.execute('select sum(amount) from account_voucher_line where voucher_id=%s and type=%s',(voucher_id,'dr',))
        aux = cr.fetchone()
        return aux[0] or 0.0
        
    def _show_retenciones(self, uid, voucher_id, context=None):
        cr = self.cr
        cr.execute('select sum(amount) from retention_tax_line where voucher_id=%s',(voucher_id,))
        aux = cr.fetchone()
        return aux[0] or 0.0
        
    def _saldo(self, original, amount, context=None):
        return original - amount


    #~ def amount_to_text_sp(self, number, currency):
        #~ #return ''
        #~ print number
        #~ units_number = int(number)
        #~ units_name = currency
        #~ if units_number > 1:
            #~ units_name += 's'
        #~ units = _10000_to_text_sp(units_number)
        #~ units = units_number and '%s %s' % (units, units_name) or ''
#~ 
    #~ #   cents_number = int(number * 100) % 100
        #~ cents_number = int(round(math.fmod(number * 100,100)))
        #~ cents_name = (cents_number > 1) and 'centavos' or 'centavo'
        #~ cents = _100_to_text_sp(cents_number)
        #~ cents = cents_number and '%s %s' % (cents, cents_name) or ''
#~ 
    #~ #   cents = '%s / 100' % (cents_number)
#~ 
        #~ if units and cents:
            #~ cents = ' '+cents
#~ 
        #~ return (cents_number > 1) and (units + ' con ' + cents) or units
        
report_sxw.report_sxw('report.account.voucher.webkit', 'account.voucher', 'addons/account_voucher_webkit/report/account_voucher.mako', parser=order, header="external")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

