# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2013 Eynes S.R.L. (http://www.eynes.com.ar) All Rights Reserved.
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

from openerp import models, fields, api
from openerp.exceptions import except_orm
from openerp.tools.translate import _


class account_checkbook(models.Model):
    _name = "account.checkbook"
    _description = "Checkbook"

    name = fields.Char('Checkbook Number', size=32, required=True)
    bank_id = fields.Many2one('res.bank', 'Bank', required=True)
    bank_account_id = fields.Many2one('res.partner.bank', 'Bank Account', required=True)
    account_check_id = fields.Many2one('account.account', 'Check Account', help="Account used for account moves with checks. If not set, account in treasury configuration is used.")
    check_ids = fields.One2many('account.checkbook.check', 'checkbook_id', 'Available Checks', domain=[('state', '=', 'draft')], readonly=True)
    issued_check_ids = fields.One2many('account.issued.check', 'checkbook_id', 'Issued Checks', readonly=True)
    # partner_id = fields.Related('company_id', 'partner_id', type="many2one", relation="res.partner", string="Partner", store=True)
    partner_id = fields.Many2one(related='company_id.partner_id', string="Partner", store=True, default=lambda self: self.env.user.company_id.partner_id.id)
    company_id = fields.Many2one('res.company', 'Company', required=True, default=lambda self: self.env.user.company_id.id)
    type = fields.Selection([('common', 'Common'), ('postdated', 'Post-dated')], 'Checkbook Type', help="If common, checks only have issued_date. If post-dated they also have payment date", default='common')

    @api.onchange('bank_account_id')
    def onchange_bank_account(self):
        self.bank_id = self.bank_account_id.bank.id

    @api.multi
    def unlink(self):
        for checkbook in self:
            if len(checkbook.issued_check_ids):
                raise except_orm(_('Error'), _('You cannot delete this checkbook because it has Issued Checks'))
            super(account_checkbook, checkbook).unlink()
        return True

    @api.model
    def _get_next_available_check(self, checkbook_id):
        check_obj = self.env["account.checkbook.check"]
        check_ids = check_obj.search([('state', '=', 'draft'), ('checkbook_id', '=', checkbook_id)], order="id asc")
        if check_ids:
            return check_ids[0]
        return False


account_checkbook()


class checkbook_check(models.Model):

    """Relacion entre Chequera y cheques por nro de cheque"""
    _name = "account.checkbook.check"
    _description = "Checkbook Check"

    name = fields.Char('Check Number', size=20, required=True)
    checkbook_id = fields.Many2one('account.checkbook', 'Checkbook number', ondelete='cascade', required=True)
    # Para tener una referencia a que cheque se convirtio
    # 'issued_check_id': fields.many2one('account.issued.check', 'Issued Check', readonly=True),
    state = fields.Selection([('draft', 'Draft'), ('done', 'Used')], 'State', readonly=True, default='draft')

checkbook_check()


class account_issued_check(models.Model):
    _inherit = 'account.issued.check'

    check_id = fields.Many2one('account.checkbook.check', 'Check')
    checkbook_id = fields.Many2one('account.checkbook', 'Checkbook')
    number = fields.Char('Check Number', size=20)

    @api.onchange('check_id')
    def onchange_check_id(self):
        checkbook = self.check_id.checkbook_id
        self.account_bank_id = checkbook.bank_account_id.id
        self.checkbook_id = checkbook.id
        self.bank_id = checkbook.bank_id.id
        self.number = self.check_id.name
        self.type = checkbook.type

    def write(self, cr, uid, ids, vals, context=None):
        a = vals.get('check_id', False)
        if a:
            sql = 'select check_id from account_issued_check where id = ' + str(ids[0])
            cr.execute(sql)
            aux_check_id = cr.fetchone()
            self.pool.get('account.checkbook.check').write(cr, uid, aux_check_id, {'state': 'draft'})
            self.pool.get('account.checkbook.check').write(cr, uid, a, {'state': 'done'})
        return super(account_issued_check, self).write(cr, uid, ids, vals, context=context)

    def create(self, cr, uid, vals, context=None):
        a = vals.get('check_id', False)
        if a:
            self.pool.get('account.checkbook.check').write(cr, uid, a, {'state': 'done'})
        return super(account_issued_check, self).create(cr, uid, vals, context=context)

    def unlink(self, cr, uid, ids, context=None):

        if not ids:
            return super(account_issued_check, self).unlink(cr, uid, ids, context=context)

        sql = 'select check_id from account_issued_check where id = ' + str(ids[0])
        cr.execute(sql)
        aux_check_id = cr.fetchone()
        self.pool.get('account.checkbook.check').write(cr, uid, aux_check_id, {'state': 'draft'})
        return super(account_issued_check, self).unlink(cr, uid, ids, context=context)

account_issued_check()
