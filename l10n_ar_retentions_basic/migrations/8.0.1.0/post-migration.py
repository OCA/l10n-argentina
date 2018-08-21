# -*- coding: utf-8 -*-

from openerp.openupgrade import openupgrade


def solve_type_with_null_values(cr):
    cr.execute("UPDATE retention_retention SET type='vat' WHERE id IN(SELECT id FROM retention_retention WHERE type IS NULL AND name ILIKE '%iva%')")  # vat
    cr.execute("UPDATE retention_retention SET type='profit' WHERE id IN(SELECT id FROM retention_retention WHERE type IS NULL AND name ILIKE '%ganancias%')")  # profit
    cr.execute("UPDATE retention_retention SET type='gross_income' WHERE id IN(SELECT id FROM retention_retention WHERE type IS NULL AND name ILIKE '%iibb%')")  # gross_income
    cr.execute("UPDATE retention_retention SET type='other' WHERE id IN(SELECT id FROM retention_retention where type IS NULL AND name NOT ILIKE '%iibb%' AND name NOT ILIKE '%ganancias%' AND name NOT ILIKE '%iva%')")  # other


@openupgrade.migrate()
def migrate(cr, version):
    if not version:
        return
    solve_type_with_null_values(cr)
