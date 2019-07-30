##############################################################################
#   Copyright (c) 2018 Eynes/E-MIPS (www.eynes.com.ar)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
##############################################################################

import logging
import os
import shlex
import tempfile
import re
from base64 import b64decode
from io import BytesIO
from zipfile import ZipFile, is_zipfile
from tempfile import mkdtemp
from subprocess import call, STDOUT
from shutil import rmtree

from odoo import registry
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError, Warning
from odoo.tools import config

_logger = logging.getLogger(__name__)

try:
    from rarfile import RarFile, is_rarfile
except (ImportError, IOError) as err:
    _logger.warning(err)


def get_dsn_pg(cr):
    """
    Receives Cursor as parameter.
    Return array with paramenter ready to be used in call to psql command.
    Also it ensures that PGPASSWORD is an Environmental Variable,
    if this is not ensured psql command fails.
    """
    env_db_pass = os.environ.get('PGPASSWORD')  # Ensure PGPASSWORD
    if not env_db_pass:  # PGPASSWORD is not an environmental variable, set it
        db_password = config.get('db_password')
        os.environ['PGPASSWORD'] = db_password
    db_name = config.get('db_name', cr.dbname)
    if not db_name:
        db_name = cr.dbname
    db_port = config.get('db_port')
    if not db_port:
        db_port = 5432
    db_user = config.get('db_user')
    assert db_user is not None, 'db_user must be set in config file'
    db_host = config.get('db_host')
    if not db_host:
        db_host = 'localhost'
    res_string = "--dbname={0} --host={1} --username={2} --port={3}".format(
        db_name, db_host, db_user, db_port)
    res_list = shlex.split(res_string)
    return res_list


class PadronImport(models.TransientModel):
    _name = 'padron.import'
    _description = 'Importer of padron file'

    datas_agip = fields.Binary('Data AGIP')
    filename_agip = fields.Char('Filename AGIP')
    datas_arba = fields.Binary('Data ARBA')
    filename_arba = fields.Char('Filename ARBA')

    @api.model
    def create_temporary_table(self):
        cursor = self.env.cr
        try:
            create_q = """
            CREATE TABLE temp_import(
                regimen varchar(2),
                create_date varchar(8),
                from_date varchar(8),
                to_date varchar(8),
                vat varchar(32),
                multilateral varchar(2),
                u1 varchar,
                u2 varchar,
                percentage varchar(10),
                u3 varchar,
                u4 varchar
            )
            """
            cursor.execute("DROP TABLE IF EXISTS temp_import")
            cursor.execute(create_q)
        except Exception:
            cursor.rollback()
            raise ValidationError(
                _("Could not create the temporary table with the file data"))
        else:
            cursor.commit()
        return True

    def correct_padron_file(self, filename):
        regex = re.compile("^((\d+;){4}(\w;){3}([\d,]+;){4})(.*)$")
        temp = tempfile.mkstemp()[1]

        f = open(filename, 'r', encoding='latin1')
        f2 = open(temp, 'w', encoding='latin1')

        for l in f.readlines():
            r = regex.match(l)
            if not r:
                continue
            # Los mostros de AGIP mandan caracteres raros o csv mal formado
            newline = r and r.groups()[0]
            f2.write(newline)
            f2.write('\n')

        f.close()
        f2.close()

        return temp

    def extract_file(self, out_path, file_like):
        files_extracted = []

        # Soportamos zip y rar
        if is_rarfile(file_like):
            z = RarFile(file_like)
        elif is_zipfile(file_like):
            z = ZipFile(file_like)
        else:
            raise ValidationError(
                _('Format of compressed file not recognized, ' +
                  'please check if it is the correct file.'))

        for name in z.namelist():
            z.extract(name, out_path)
            files_extracted.append(out_path + '/' + name)

        return files_extracted

    @api.model
    def import_agip_file(self, rar_file_agip):
        _logger.info('[AGIP] Inicio de importacion')
        dsn_pg_splitted = get_dsn_pg(self.env.cr)
        decoded = b64decode(rar_file_agip)
        file_like = BytesIO(decoded)
        out_path = mkdtemp()
        files_extracted = self.extract_file(out_path, file_like)

        _logger.info('[AGIP] Files extracted: ' + str(len(files_extracted)))
        if len(files_extracted) != 1:
            raise ValidationError(
                _("Expected only one file compressed, got: %d") %
                len(files_extracted))

        # Corregimos porque los craneos de AGIP hacen mal el arhivo,
        # metiendo ; donde no deberian ir
        txt_path = self.correct_padron_file(files_extracted[0])
        dbname = self.env.cr.dbname
        cursor = registry(dbname).cursor()  # Get a new cursor
        try:
            _logger.info('[AGIP] Creando tabla temporal')
            create_q = """
            CREATE TABLE temp_import(
            create_date varchar(8),
            from_date varchar(8),
            to_date varchar(8),
            vat varchar(32),
            multilateral varchar(2),
            u1 varchar,
            u2 varchar,
            percentage_perception varchar(10),
            percentage_retention varchar(10),
            group_per varchar,
            group_ret varchar,
            name_partner varchar
            )
            """
            cursor.execute("DROP TABLE IF EXISTS temp_import")
            cursor.execute(create_q)
        except Exception:
            cursor.rollback()
            raise ValidationError(
                _("Could not create the temporary table with the file data"))
        else:
            cursor.commit()

        _logger.info('[AGIP] Copiando del csv a tabla temporal')
        psql_args_list = [
            "psql",
            "--command=\copy temp_import(create_date,from_date,to_date,vat,multilateral,u1,u2,percentage_perception,percentage_retention,group_per,group_ret,name_partner) FROM " + txt_path + " WITH DELIMITER ';' NULL '' CSV QUOTE E'\b' ENCODING 'latin1'"  # noqa
        ]
        psql_args_list[1:1] = dsn_pg_splitted
        retcode = call(psql_args_list, stderr=STDOUT)
        assert retcode == 0, \
            "Call to psql subprocess copy command returned: " + str(retcode)

        try:
            # TODO: Creacion de los grupos de retenciones y percepciones
            _logger.info('[AGIP] Verificando grupos')

            _logger.info('[AGIP] Copiando de tabla temporal a definitiva')
            query = """
            INSERT INTO padron_agip_percentages
            (create_uid, create_date, write_date, write_uid,
            from_date, to_date, percentage_perception, percentage_retention,
            vat, multilateral, name_partner)
            SELECT 1 as create_uid,
            to_date(create_date, 'DDMMYYYY'),
            current_date,
            1,
            to_date(from_date, 'DDMMYYYY'),
            to_date(to_date, 'DDMMYYYY'),
            to_number(percentage_perception, '999.99')/100,
            to_number(percentage_retention, '999.99')/100,
            vat,
            (CASE
                WHEN multilateral = 'C' THEN True
                ELSE False
            END) as multilateral,
            name_partner FROM temp_import
            """
            cursor.execute("DELETE FROM padron_agip_percentages")
            cursor.execute(query)
            cursor.execute("DROP TABLE IF EXISTS temp_import")
        except Exception:
            cursor.rollback()
            _logger.warning('[AGIP] ERROR: Rollback')
        else:
            # Mass Update
            mass_wiz_obj = self.env['padron.mass.update']
            wiz = mass_wiz_obj.create({
                'arba': False,
                'agip': True,
            })
            # TODO
            wiz.action_update()

            cursor.commit()
            _logger.info('[AGIP] SUCCESS: Fin de carga de padron de agip')

        finally:
            rmtree(out_path)  # Delete temp folder
            cursor.close()
        return True

    @api.model
    def import_arba_file(self, zip_file_arba):
        _logger.info('[ARBA] Inicio de importacion')
        dsn_pg_splitted = get_dsn_pg(self.env.cr)
        decoded = b64decode(zip_file_arba)
        file_like = BytesIO(decoded)
        out_path = mkdtemp()
        files_extracted = self.extract_file(out_path, file_like)

        _logger.info('[ARBA] Files extracted: ' + str(len(files_extracted)))
        if len(files_extracted) != 2:
            raise ValidationError(
                _('Expected two files compressed, got: %d') %
                len(files_extracted))

        dbname = self.env.cr.dbname
        cursor = registry(dbname).cursor()  # Get a new cursor
        for file_name in files_extracted:
            txt_path = "'" + file_name + "'"
            if 'Ret' in file_name:
                _logger.info('[ARBA] Ret - Inicio de carga ')
                # copiar a postgresql padron_arba_retention
                self.create_temporary_table()
                _logger.info('[ARBA] Ret - Copiando a tabla temporal')
                psql_args_list = [
                    "psql",
                    "--command=\copy temp_import(regimen,create_date,from_date,to_date,vat,multilateral,u1,u2,percentage,u3,u4) FROM " + txt_path + " WITH DELIMITER ';' NULL '' "  # noqa
                ]
                psql_args_list[1:1] = dsn_pg_splitted
                retcode = call(psql_args_list, stderr=STDOUT)
                assert retcode == 0, 'Call expected return 0'
                try:
                    query = """
                    INSERT INTO padron_arba_retention
                    (create_uid, create_date, write_date, write_uid,
                    vat, percentage, from_date, to_date, multilateral)
                    SELECT 1 as create_uid,
                    to_date(create_date,'DDMMYYYY'),
                    current_date,
                    1,
                    vat,
                    to_number(percentage, '999.99')/100,
                    to_date(from_date,'DDMMYYYY'),
                    to_date(to_date,'DDMMYYYY'),
                    (CASE
                        WHEN multilateral = 'C'
                        THEN True ELSE False
                    END) as multilateral
                    FROM temp_import
                    """
                    cursor.execute("DELETE FROM padron_arba_retention")
                    _logger.info('[ARBA] Ret - Copiando a tabla definitiva')
                    cursor.execute(query)
                    cursor.execute("DROP TABLE IF EXISTS temp_import")
                except Exception:
                    cursor.rollback()
                    _logger.warning('[ARBA]ERROR: Rollback')
                else:
                    cursor.commit()
                    _logger.info('[ARBA]SUCCESS: Fin de carga de retenciones')
            if 'Per' in file_name:
                self.create_temporary_table()
                _logger.info('[ARBA] Per - Copiando a tabla temporal')
                psql_args_list = [
                    "psql",
                    "--command=\copy temp_import(regimen,create_date,from_date,to_date,vat,multilateral,u1,u2,percentage,u3,u4) FROM " + txt_path + " WITH DELIMITER ';' NULL '' "  # noqa
                ]
                psql_args_list[1:1] = dsn_pg_splitted
                retcode = call(psql_args_list, stderr=STDOUT)
                assert retcode == 0, 'Call expected return 0'
                try:
                    query = """
                    INSERT INTO padron_arba_perception
                    (create_uid, create_date, write_date, write_uid,
                    vat, percentage, from_date, to_date, multilateral)
                    SELECT 1 as create_uid,
                    to_date(create_date,'DDMMYYYY'),
                    current_date,
                    1,
                    vat,
                    to_number(percentage, '999.99')/100,
                    to_date(from_date,'DDMMYYYY'),
                    to_date(to_date,'DDMMYYYY'),
                    (CASE
                        WHEN multilateral = 'C'
                        THEN True ELSE False
                    END) as multilateral
                    FROM temp_import
                    """
                    cursor.execute("DELETE FROM padron_arba_perception")
                    _logger.info('[ARBA] Per - Copiando a tabla definitiva')
                    cursor.execute(query)
                    cursor.execute("DROP TABLE IF EXISTS temp_import")
                except Exception:
                    cursor.rollback()
                    _logger.warning('[ARBA]ERROR: Rollback')
                else:
                    # Mass Update
                    mass_wiz_obj = self.env['padron.mass.update']
                    wiz = mass_wiz_obj.create({
                        'arba': True,
                        'agip': False,
                    })
                    # TODO
                    wiz.action_update()

                    cursor.commit()
                    _logger.info('[ARBA]SUCCESS: Fin de carga de percepciones')
        rmtree(out_path)  # Delete temp folder
        cursor.close()
        return True

    @api.multi
    def import_zip_file(self):
        self.ensure_one()
        if self.datas_agip:
            _logger.info('[AGIP] Zip file from AGIP is loaded: START')
            self.import_agip_file(self.datas_agip)
        if self.datas_arba:
            _logger.info('[ARBA] Zip file from ARBA is loaded: START')
            self.import_arba_file(self.datas_arba)

        raise Warning(_("Hey!\nThe import ended Successfully"))
