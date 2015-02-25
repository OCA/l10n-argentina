#!/usr/bin/python
# -*- coding: utf-8 -*-
##############################################################################
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see http://www.gnu.org/licenses/.
#
#    Copyright 2013 E-MIPS
##############################################################################
from osv import fields, osv
from tools.translate import _

import xmlrpclib
import argparse
import sys
import os
import base64
from xml.dom import minidom
from datetime import datetime
import xlrd

from tools import DEFAULT_SERVER_DATETIME_FORMAT

#~ TO_READ = {
    #~ 'Project': ['Name'],
    #~ 'Resource': ['UID', 'Name', 'Group'],
    #~ 'Task': ['UID', 'Name', 'Priority', 'Start', 'Finish', 'ExtendedAttribute', 'OutlineLevel'],
    #~ 'Assignment': ['TaskUID', 'ResourceUID'],
#~ }

class project_import(osv.osv_memory):
    _name = "project.import"
    _description = "Import Project"

    def get_value(self, element, tag):
        value = element.getElementsByTagName(tag) or False
        return value and value[0].firstChild.nodeValue

    def save_file(self, name, value):
        path = os.path.abspath(os.path.dirname(__file__))
        path += '/xml/%s' % name
        f = open(path, 'wb+')
        try:
            f.write(base64.decodestring(value))
        finally:
            f.close()
        return path

    _columns = {
        'file': fields.binary('File', filename="filename"),
        'filename': fields.char('Filename', size=256),
        }
        
    def read_xml(self, path):
        xmldoc = minidom.parse(path)
        res = {}
        
        for index in TO_READ:
            res[index] = []
            for value in xmldoc.getElementsByTagName(index):
                res[index].append(dict([(tag, self.get_value(value, tag)) for tag in TO_READ[index]]))

        return res
    
    # Creamos empleado, recurso y usuario asociado.
    #~ def create_employee(self, cr, uid, data, context=None):
#~ 
        #~ user_obj = self.pool.get('res.users')
        #~ resource_obj = self.pool.get('resource.resource')
        #~ job_obj = self.pool.get('hr.job')
        #~ employee_obj = self.pool.get('hr.employee')
        #~ 
        #~ # Chequeamos si el usuario ya existe
        #~ user_id = user_obj.search(cr, uid, [('import_id', '=', int(data['UID']))], context=context)
#~ 
        #~ # Si no existe lo creamos y agregamos a la categoria
        #~ if not user_id:
            #~ user_id = user_obj.create(cr, uid, {
                #~ 'import_id': data['UID'],
                #~ 'name': data['Name'],
                #~ 'login': data['Name']
            #~ }, context=context)
        #~ else:
            #~ user_id = user_id[0]
            #~ 
        #~ # Chequeamos si el recurso ya existe
        #~ resource_id = resource_obj.search(cr, uid, [('import_id', '=', int(data['UID']))], context=context)
#~ 
        #~ # Si no existe lo creamos y agregamos a la categoria
        #~ if not resource_id:
            #~ resource_id = resource_obj.create(cr, uid, {
                #~ 'import_id': data['UID'],
                #~ 'name': data['Name'],
                #~ 'user_id': user_id
            #~ }, context=context)
        #~ else:
            #~ resource_id = resource_id[0]
        #~ 
        #~ job_id = False
        #~ 
        #~ if data['Group']:
        #~ 
            #~ # Chequeamos si existe el trabajo
            #~ job_id = job_obj.search(cr, uid, [('name', 'ilike', data['Group'])], context=context)
#~ 
            #~ # Si no existe la creamos
            #~ if not job_id:
                #~ job_id = job_obj.create(cr, uid, {'name': data['Group']}, context=context)
            #~ else:
                #~ job_id = job_id[0]
#~ 
        #~ # Chequeamos si el empleado ya existe
        #~ employee_id = employee_obj.search(cr, uid, [('import_id', '=', int(data['UID']))], context=context)
#~ 
        #~ # Si no existe lo creamos y agregamos a la categoria
        #~ if not employee_id:
            #~ employee_id = employee_obj.create(cr, uid, {
                #~ 'import_id': data['UID'],
                #~ 'name': data['Name'],
                #~ 'job_id': job_id,
                #~ 'resource_id': resource_id
            #~ }, context=context)
        #~ else:
            #~ employee_id = employee_id[0]
        #~ 
        #~ return user_id
#~ 
    #~ def create_project(self, cr, uid, data, members, context=None):
        #~ 
        #~ project_obj = self.pool.get('project.project')
        #~ 
        #~ # Chequeamos si existe el proyecto
        #~ project_id = project_obj.search(cr, uid, [('name', 'ilike', data['Name'])], context=context)
#~ 
        #~ # Si no existe lo creamos
        #~ if not project_id:
            #~ project_id = project_obj.create(cr, uid, {
                #~ 'name': data['Name'][:-4],
                #~ 'members': [(6, 0, members)]
            #~ }, context=context)
        #~ else:
            #~ project_id = project_id[0]
            #~ 
        #~ return project_id
#~ 
    #~ def _find_parent_id(self, last_parent_ids, outline_level):
        #~ for index in range(len(last_parent_ids)-1,-1,-1):
            #~ if last_parent_ids[index][0] == outline_level-1:
                #~ return last_parent_ids[index][1]
#~ 
    #~ def create_task_or_phase(self, cr, uid, data, project_id, last_parent_ids, context=None):
        #~ 
        #~ task_obj = self.pool.get('project.task')
        #~ phase_obj = self.pool.get('project.phase')
        #~ 
        #~ current_id = int(data['UID'])
#~ 
        #~ if data['ExtendedAttribute']:
            #~ task_id = task_obj.search(cr, uid, [('import_id', '=', current_id)], context=context)
        #~ else:
            #~ task_id = phase_obj.search(cr, uid, [('import_id', '=', current_id)], context=context)
        #~ 
        #~ if not len(task_id):
            #~ 
            #~ insert_data = {
                #~ 'import_id': current_id,
                #~ 'name': data['Name'],
                #~ 'project_id': project_id,
                #~ 'date_start': data['Start'],
                #~ 'date_end': data['Finish']
            #~ }
            #~ 
            #~ start_date = datetime.strptime(data['Start'], '%Y-%m-%dT%H:%M:%S')
            #~ finish_date = datetime.strptime(data['Finish'], '%Y-%m-%dT%H:%M:%S')
            #~ duration = (finish_date - start_date).days
            #~ 
            #~ if data['ExtendedAttribute']:
                #~ insert_data.update({
                    #~ 'phase_id': self._find_parent_id(last_parent_ids, data['OutlineLevel'])
                #~ })
                #~ task_obj.create(cr, uid, insert_data, context=context)
                #~ 
                #~ return 
            #~ else:
                #~ insert_data.update({
                    #~ 'duration': duration
                #~ })
                #~ 
                #~ if data['OutlineLevel'] > 1:
                    #~ insert_data['parent_id'] = self._find_parent_id(last_parent_ids, data['OutlineLevel'])
                #~ 
                #~ return phase_obj.create(cr, uid, insert_data, context=context)
#~ 
        #~ return task_id[0]
        #~ 
    #~ def create_assignment(self, cr, uid, data, context=None):
        #~ 
        #~ task_obj = self.pool.get('project.task')
        #~ user_obj = self.pool.get('res.users')        
        #~ 
        #~ task_id = task_obj.search(cr, uid, [('import_id', '=', int(data['TaskUID']))], context=context)
        #~ if not task_id:
            #~ return
        #~ else:
            #~ task_id = task_id[0]
        #~ 
        #~ user_id = user_obj.search(cr, uid, [('import_id', '=', int(data['ResourceUID']))], context=context)
        #~ if not user_id:
            #~ return
        #~ else:
            #~ user_id = user_id[0]
        #~ 
        #~ task_obj.write(cr, uid, task_id, {'user_id': user_id}, context=context)
        #~ 
        #~ return
            
	def read(path):
		book = xlrd.open_workbook(path)
		sheet = book.sheet_by_index(0)
		res = []
		for row in range(1, sheet.nrows):
			res.append({
				'date': sheet.cell_value(row, 0),
				'description': sheet.cell_value(row, 1),
				#'name': sheet.cell_value(row, 3)
			})
			
		print res
			
		return res
		
    def read_file(self, cr, uid, id, context=None):
    
        for form in self.browse(cr, uid, id, context=context):
            selected_file = form.file
            if not selected_file:
                raise osv.except_osv(('Error 501'),('You must select at least one file before continue'))
        
            path = self.save_file(form.filename, form.file)
            result = self.read_xml(path)
            
            self.read(path)
            #~ users = []
            #~ for employee in result['Resource']:
                #~ users.append(self.create_employee(cr, uid, employee, context))
                #~ 
            #~ for project in result['Project']:
                #~ project_id = self.create_project(cr, uid, project, users, context)
#~ 
            #~ last_parent_ids = []
            #~ for task in result['Task']:
                #~ task['OutlineLevel'] = int(task['OutlineLevel'])
                #~ inserted = self.create_task_or_phase(cr, uid, task, project_id, last_parent_ids, context)
                #~ 
                #~ if inserted:
                    #~ last_parent_ids.append((task['OutlineLevel'], inserted))
                #~ 
            #~ for assignment in result['Assignment']:
                #~ self.create_assignment(cr, uid, assignment, context)
                    
        return {'type': 'ir.actions.act_window_close'}

project_import()
