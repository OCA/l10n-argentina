##############################################################################
#   Copyright (c) 2018 Eynes/E-MIPS (www.eynes.com.ar)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
##############################################################################

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class PadronMassUpdate(models.TransientModel):
    _name = 'padron.mass.update'
    _description = 'Padron Mass Update'

    arba = fields.Boolean('Update ARBA')
    agip = fields.Boolean('Update AGIP')

    @api.model
    def _update_retention_arba(self, retention_id):
        cr = self.env.cr
        query = """
        WITH padron AS (
            SELECT
                rp.id p_partner_id,
                par.percentage p_percentage,
                par.multilateral p_multilateral
            FROM res_partner rp
                JOIN padron_arba_retention par ON par.vat=rp.vat
            WHERE
                rp.parent_id IS NULL
                AND rp.supplier
        ),
        retentions AS (
            SELECT
                rpr.id r_id,
                rpr.partner_id r_partner_id,
                rpr.percent r_percentage
            FROM res_partner_retention rpr
            WHERE rpr.retention_id=%s
        )
        SELECT * FROM (SELECT padron.*, retentions.*,
            CASE
                WHEN (p_partner_id IS NOT NULL)
                    AND (r_partner_id IS NOT NULL)
                    AND (p_percentage <> r_percentage)
                    THEN 'UPDATE'  -- In padron and sys
                WHEN (p_partner_id IS NOT NULL)
                    AND (r_partner_id IS NOT NULL)
                    AND (p_percentage = r_percentage)
                    THEN 'NONE'  -- In padron and sys but same percent
                WHEN (p_partner_id IS NOT NULL) AND
                    (r_partner_id IS NULL)
                    THEN 'CREATE'  -- In padron not in sys
                WHEN (p_partner_id IS NULL)
                    AND (r_partner_id IS NOT NULL)
                    THEN 'DELETE'  -- Not in padron but in sys
                ELSE 'ERROR' -- Never should enter here
            END umode
            FROM padron
                FULL JOIN retentions
                ON retentions.r_partner_id=padron.p_partner_id) z
        WHERE umode != 'NONE';
        """

        params = (retention_id, )
        cr.execute(query, params)

        for res in cr.fetchall():
            if res[6] == 'UPDATE':  # Change the amount of percentage
                q = """
                UPDATE res_partner_retention SET
                    percent=%(percent)s,
                    from_padron = True
                WHERE id=%(id)s
                """
                q_params = {
                    'percent': res[1],
                    'id': res[3],
                }
                self._cr.execute(q, q_params)
            elif res[6] == 'DELETE':   # Set the percentage to -1
                q = """
                UPDATE res_partner_retention SET
                    percent=%(percent)s,
                    from_padron = True
                WHERE id=%(id)s
                """
                q_params = {
                    'percent': -1,
                    'id': res[3],
                }
                self._cr.execute(q, q_params)
            elif res[6] == 'CREATE':  # Create the res.partner.retention
                q = """
                INSERT INTO res_partner_retention (
                    partner_id,
                    percent,
                    retention_id,
                    from_padron
                ) VALUES (
                    %(partner_id)s,
                    %(percent)s,
                    %(retention_id)s,
                    True
                )"""
                q_params = {
                    'percent': res[1],
                    'partner_id': res[0],
                    'retention_id': retention_id,
                }
                self._cr.execute(q, q_params)
            else:
                e_title = _('Query Error\n')
                e_msg = _('Unexpected result: %s' % res)
                raise ValidationError(e_title + e_msg)

    @api.model
    def _update_perception_arba(self, perception_id):
        multilateral_record = self.env.ref(
            'l10n_ar_point_of_sale.iibb_situation_multilateral')
        local_record = self.env.ref(
            'l10n_ar_point_of_sale.iibb_situation_local')
        cr = self.env.cr
        query = """
        WITH padron AS (
            SELECT
                rp.id p_partner_id,
                par.percentage p_percentage,
                par.multilateral p_multilateral
            FROM res_partner rp
                JOIN padron_arba_perception par ON par.vat=rp.vat
            WHERE
                rp.parent_id IS NULL
                AND rp.customer
        ),
        perceptions AS (
            SELECT
                rpp.id r_id,
                rpp.partner_id r_partner_id,
                rpp.percent r_percentage
            FROM res_partner_perception rpp
            WHERE rpp.perception_id=%s
        )
        SELECT * FROM (SELECT padron.*, perceptions.*,
            CASE
                WHEN (p_partner_id IS NOT NULL)
                    AND (r_partner_id IS NOT NULL)
                    AND (p_percentage <> r_percentage)
                    THEN 'UPDATE'  -- In padron and sys
                WHEN (p_partner_id IS NOT NULL)
                    AND (r_partner_id IS NOT NULL)
                    AND (p_percentage = r_percentage)
                    THEN 'NONE'  -- In padron and sys but same percent
                WHEN (p_partner_id IS NOT NULL)
                    AND (r_partner_id IS NULL)
                    THEN 'CREATE'  -- In padron not in sys
                WHEN (p_partner_id IS NULL)
                    AND (r_partner_id IS NOT NULL)
                    THEN 'DELETE'  -- Not in padron but in sys
                ELSE 'ERROR' -- Never should enter here
            END umode
            FROM padron
                FULL JOIN perceptions
                ON perceptions.r_partner_id=padron.p_partner_id) z
        WHERE umode != 'NONE';
        """

        params = (perception_id, )
        cr.execute(query, params)

        for res in cr.fetchall():
            if res[6] == 'UPDATE':  # Change the amount of percentage
                q = "UPDATE res_partner_perception SET percent=%(percent)s, \
                    from_padron = True WHERE id=%(id)s"
                q_params = {'percent': res[1], 'id': res[3]}
                self._cr.execute(q, q_params)
            elif res[6] == 'DELETE':   # Set the percentage to -1
                q = "UPDATE res_partner_perception SET percent=%(percent)s, \
                    from_padron = True WHERE id=%(id)s"
                q_params = {'percent': -1, 'id': res[3]}
                self._cr.execute(q, q_params)
            elif res[6] == 'CREATE':  # Create the res.partner.perception
                q = """
                INSERT INTO res_partner_perception (
                    partner_id,
                    percent,
                    perception_id,
                    from_padron,
                    sit_iibb
                ) VALUES (
                    %(partner_id)s,
                    %(percent)s,
                    %(perception_id)s,
                    True,
                    %(sit_iibb)s
                )"""
                q_params = {
                    'percent': res[1],
                    'partner_id': res[0],
                    'perception_id': perception_id,
                    'sit_iibb': multilateral_record.id if res[2]
                    else local_record.id,
                }
                self._cr.execute(q, q_params)
            else:
                e_title = _('Query Error\n')
                e_msg = _('Unexpected result: %s' % res)
                raise ValidationError(e_title + e_msg)

    @api.model
    def _update_retention_agip(self, retention_id):
        cr = self.env.cr
        query = """
        WITH padron AS (
            SELECT
                rp.id p_partner_id,
                par.percentage_retention p_percentage,
                par.multilateral p_multilateral
            FROM res_partner rp
                JOIN padron_agip_percentages par ON par.vat=rp.vat
            WHERE
                rp.parent_id IS NULL
                AND rp.supplier
        ),
        retentions AS (
            SELECT
                rpr.id r_id,
                rpr.partner_id r_partner_id,
                rpr.percent r_percentage
            FROM res_partner_retention rpr
            WHERE rpr.retention_id=%s
        )
        SELECT * FROM (SELECT padron.*, retentions.*,
            CASE
                WHEN (p_partner_id IS NOT NULL)
                    AND (r_partner_id IS NOT NULL)
                    AND (p_percentage <> r_percentage)
                    THEN 'UPDATE'  -- In padron and sys
                WHEN (p_partner_id IS NOT NULL)
                    AND (r_partner_id IS NOT NULL)
                    AND (p_percentage = r_percentage)
                    THEN 'NONE'  -- In padron and sys but same percent
                WHEN (p_partner_id IS NOT NULL)
                    AND (r_partner_id IS NULL)
                    THEN 'CREATE'  -- In padron not in sys
                WHEN (p_partner_id IS NULL)
                    AND (r_partner_id IS NOT NULL)
                    THEN 'DELETE'  -- Not in padron but in sys
                ELSE 'ERROR' -- Never should enter here
            END umode
            FROM padron
                FULL JOIN retentions
                ON retentions.r_partner_id=padron.p_partner_id)
        z WHERE umode != 'NONE';
        """

        params = (retention_id, )
        cr.execute(query, params)

        for res in cr.fetchall():
            if res[6] == 'UPDATE':  # Change the amount of percentage
                q = """
                UPDATE res_partner_retention SET
                    percent=%(percent)s
                    from_padron = True
                WHERE id=%(id)s
                """
                q_params = {
                    'percent': res[1],
                    'id': res[3],
                }
                self._cr.execute(q, q_params)
            elif res[6] == 'DELETE':   # Set the percentage to -1
                q = """
                UPDATE res_partner_retention SET
                    percent=%(percent)s
                    from_padron = True
                WHERE id=%(id)s
                """
                q_params = {
                    'percent': -1,
                    'id': res[3],
                }
                self._cr.execute(q, q_params)
            elif res[6] == 'CREATE':  # Create the res.partner.retention
                q = """
                INSERT INTO res_partner_retention (
                    partner_id,
                    percent,
                    retention_id,
                    from_padron
                ) VALUES (
                    %(partner_id)s,
                    %(percent)s,
                    %(retention_id)s,
                    True
                )"""
                q_params = {
                    'percent': res[1],
                    'partner_id': res[0],
                    'retention_id': retention_id,
                }
                self._cr.execute(q, q_params)
            else:
                e_title = _('Query Error\n')
                e_msg = _('Unexpected result: %s' % res)
                raise ValidationError(e_title + e_msg)

    @api.model
    def _update_perception_agip(self, perception_id):
        cr = self.env.cr
        query = """
        WITH padron AS (
            SELECT
                rp.id p_partner_id,
                par.percentage_perception p_percentage,
                par.multilateral p_multilateral
            FROM res_partner rp
                JOIN padron_agip_percentages par ON par.vat=rp.vat
            WHERE
                rp.parent_id IS NULL
                AND rp.customer
        ),
        perceptions AS (
            SELECT
                rpr.id r_id,
                rpr.partner_id r_partner_id,
                rpr.percent r_percentage
            FROM res_partner_perception rpr
            WHERE rpr.perception_id=%s
        )
        SELECT * FROM (SELECT padron.*, perceptions.*,
            CASE
                WHEN (p_partner_id IS NOT NULL)
                    AND (r_partner_id IS NOT NULL)
                    AND (p_percentage <> r_percentage)
                    THEN 'UPDATE'  -- In padron and sys
                WHEN (p_partner_id IS NOT NULL)
                    AND (r_partner_id IS NOT NULL)
                    AND (p_percentage = r_percentage)
                    THEN 'NONE'  -- In padron and sys but same percent
                WHEN (p_partner_id IS NOT NULL)
                    AND (r_partner_id IS NULL)
                    THEN 'CREATE'  -- In padron not in sys
                WHEN (p_partner_id IS NULL)
                    AND (r_partner_id IS NOT NULL)
                    THEN 'DELETE'  -- Not in padron but in sys
                ELSE 'ERROR' -- Never should enter here
            END umode
            FROM padron
                FULL JOIN perceptions
                ON perceptions.r_partner_id=padron.p_partner_id) z
        WHERE umode != 'NONE';
        """

        params = (perception_id, )
        cr.execute(query, params)

        for res in cr.fetchall():
            if res[6] == 'UPDATE':  # Change the amount of percentage
                q = """
                UPDATE res_partner_perception SET
                    percent=%(percent)s,
                    from_padron = True
                WHERE id=%(id)s
                """
                q_params = {
                    'percent': res[1],
                    'id': res[3],
                }
                self._cr.execute(q, q_params)
            elif res[6] == 'DELETE':   # Set the percentage to -1
                q = """
                UPDATE res_partner_perception SET
                    percent=%(percent)s
                    from_padron = True
                WHERE id=%(id)s
                """
                q_params = {
                    'percent': -1,
                    'id': res[3],
                }
                self._cr.execute(q, q_params)
            elif res[6] == 'CREATE':  # Create the res.partner.perception
                q = """
                INSERT INTO res_partner_perception (
                    partner_id,
                    percent,
                    perception_id,
                    from_padron
                ) VALUES (
                    %(partner_id)s,
                    %(percent)s,
                    %(perception_id)s,
                    True
                )"""
                q_params = {
                    'percent': res[1],
                    'partner_id': res[0],
                    'perception_id': perception_id,
                }
                self._cr.execute(q, q_params)
            else:
                e_title = _('Query Error\n')
                e_msg = _('Unexpected result: %s' % res)
                raise ValidationError(e_title + e_msg)

    @api.multi
    def action_update(self):
        perception_obj = self.env['perception.perception']
        retention_obj = self.env['retention.retention']
        if self.arba:
            # Actualizamos Percepciones
            percep_arba = perception_obj._get_perception_from_arba()
            if not percep_arba:
                raise ValidationError(
                    _("Perception Error!\n") +
                    _("There is no perception configured to update " +
                      "from Padron ARBA"))
            self._update_perception_arba(percep_arba[0].id)
            # Actualizamos Retenciones
            retent_arba = retention_obj._get_retention_from_arba()
            if not retent_arba:
                raise ValidationError(
                    _("Retention Error!\n") +
                    _("There is no retention configured to update " +
                      "from Padron ARBA"))
            self._update_retention_arba(retent_arba[0].id)
        if self.agip:
            # Actualizamos Percepciones
            percep_agip = perception_obj._get_perception_from_agip()
            if not percep_agip:
                raise ValidationError(
                    _("Perception Error!\n") +
                    _("There is no perception configured to update " +
                      "from Padron AGIP"))
            self._update_perception_agip(percep_agip[0].id)
            # Actualizamos Retenciones
            retent_agip = retention_obj._get_retention_from_agip()
            if not retent_agip:
                raise ValidationError(
                    _("Retention Error!\n") +
                    _("There is no retention configured to update " +
                      "from Padron AGIP"))
            self._update_retention_agip(retent_agip[0].id)

        return True
