# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2016 E-MIPS (http://www.e-mips.com.ar)
#    Copyright (c) 2016 Eynes (http://www.eynes.com.ar)
#    Copyright (c) 2016 Aconcagua Team (http://www.aconcagua.com.ar)
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
# Le agregamos feature de multimoneda a este modulo, por lo tanto vamos a usar
# los campos base_code_amount y tax_code_amount que no estaban siendo usados y los
# debemos llenar con lo mismo que el base y amount respectivamente
__name__ = u"Popula las columnas tax_code_amount y base_code_amount por multimoneda"


def populate_base_tax_code_amount_columns(cr):
    cr.execute("""
        UPDATE perception_tax_line SET tax_amount=amount, base_amount=base
        """)

def migrate(cr, version):
    if not version:
        return
    populate_base_tax_code_amount_columns(cr)
