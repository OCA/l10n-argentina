# -*- coding: utf-8 -*-

import psycopg2


def _do_update(cr):
    """
    1. Generate missing journals for payments.mode.receipt
    2. Update payment.mode.receipt.line to point the corrects journals
    """
    try:
        cr.execute("ALTER TABLE account_journal ALTER COLUMN code TYPE varchar(10)")
        cr.execute("ALTER TABLE payment_mode_receipt_line DROP CONSTRAINT IF EXISTS payment_mode_receipt_line_payment_mode_id_fkey")
        cr.execute("""
            SELECT DISTINCT pmr.account_id, acc.name, pmr.company_id, acc.code
            FROM payment_mode_receipt pmr LEFT JOIN account_journal aj ON pmr.account_id=aj.default_debit_account_id AND pmr.account_id = aj.default_credit_account_id
            JOIN account_account acc ON acc.id = pmr.account_id
            WHERE aj.id IS NULL;
        """)
        aj_to_create = cr.fetchall()
        for aj in aj_to_create:
            acc_id, name, company_id, code = aj
            # Generate sequence
            q = """
                INSERT INTO ir_sequence
                (implementation, name, number_increment, number_next, padding)
                VALUES
                (%(implementation)s, %(name)s, %(number_increment)s, %(number_next)s, %(padding)s)
                RETURNING id
            """
            q_params = {
                'implementation': 'no_gap',
                'name': name,
                'number_increment': 1,
                'number_next': 1,
                'padding': 4,
            }
            cr.execute(q, q_params)
            seq_id = cr.fetchone()[0]
            # Generate the journal
            q = """
                INSERT INTO account_journal
                (code, company_id, name, sequence_id, type, default_debit_account_id, default_credit_account_id)
                VALUES
                (%(code)s, %(company_id)s, %(name)s, %(sequence_id)s, %(type)s, %(debit_acc)s, %(credit_acc)s)
                RETURNING id
            """
            q_params = {
                'code': code,
                'company_id': company_id,
                'name': name,
                'sequence_id': seq_id,
                'type': 'bank',
                'debit_acc': acc_id,
                'credit_acc': acc_id,
            }
            cr.execute(q, q_params)
            aj_id = cr.fetchone()[0]
        # All required journals are created: Set the corresponding journal to the payment_mode_receipt
        cr.execute("ALTER TABLE payment_mode_receipt DROP COLUMN IF EXISTS journal_id;")
        cr.execute("ALTER TABLE payment_mode_receipt ADD COLUMN journal_id INTEGER;")
        cr.execute("""
            WITH q1 AS (
                SELECT pmr.id pmr_id, pmr.account_id, acc.name, pmr.company_id, acc.code, aj.id aj_id
                FROM payment_mode_receipt pmr JOIN account_journal aj ON pmr.account_id=aj.default_debit_account_id AND pmr.account_id = aj.default_credit_account_id
                JOIN account_account acc ON acc.id = pmr.account_id
                WHERE aj.id IS NOT NULL)
            UPDATE payment_mode_receipt SET journal_id = q1.aj_id FROM q1 WHERE id=q1.pmr_id;
        """)
        # Have a reference to the payment_mode_receipt
        cr.execute("ALTER TABLE payment_mode_receipt_line DROP COLUMN IF EXISTS old_payment_mode_id;")
        cr.execute("ALTER TABLE payment_mode_receipt_line ADD COLUMN old_payment_mode_id INTEGER;")
        cr.execute("UPDATE payment_mode_receipt_line SET old_payment_mode_id=payment_mode_id")
        # Update to set the journal as the payment_mode_id
        cr.execute("""
            WITH q1 AS (
                SELECT pmrl.id, pmr.journal_id FROM payment_mode_receipt_line pmrl
                JOIN payment_mode_receipt pmr ON pmrl.old_payment_mode_id=pmr.id
            ) UPDATE payment_mode_receipt_line pmrl2 SET payment_mode_id=q1.journal_id FROM q1 WHERE pmrl2.id=q1.id;
        """)
    except psycopg2.ProgrammingError:
        cr.rollback()
    else:
        cr.commit()


def migrate(cr, installed_version):
    return _do_update(cr)
