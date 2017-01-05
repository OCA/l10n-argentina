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
__name__ = u"Cambia nombre de las columnas tax_amount y base_amount para multimoneda"

from psycopg2 import ProgrammingError
import logging

logger = logging.getLogger(__name__)

def migrate(cr, version):
    if not version:
        return
    import ipdb; ipdb.set_trace()
    try:
        cr.execute("""
            ALTER TABLE perception_tax_line RENAME COLUMN tax_amount TO tax_currency
            """)

        cr.execute("""
            ALTER TABLE perception_tax_line RENAME COLUMN base_amount TO base_currency
            """)
    except ProgrammingError:
        logger.info("Migration already applied.")
        cr.rollback()


