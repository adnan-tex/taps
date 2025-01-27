import base64
import io
import logging
from odoo import models, fields, api
from datetime import datetime, date, timedelta, time
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import xlsxwriter
from odoo.tools import format_date
import re
import math
_logger = logging.getLogger(__name__)

class HeadwisePDFReport(models.TransientModel):
    _name = 'kpi.objective.pdf.report'
    _description = 'KPI Objective Report'    

    is_company = fields.Boolean(readonly=False, default=False)
    date_from = fields.Date('Date from', required=False, default = (date.today().replace(day=1) - timedelta(days=1)).strftime('%Y-%m-26'))
    date_to = fields.Date('Date to', required=False, default = fields.Date.today().strftime('%Y-%m-25'))
    report_type = fields.Selection([
        ('score',	'Scorecard'),
        ('scorequarter',	'Scorecard Quarterly'),
        ('kpi',	'KPI Objective'),
        ('plan',	'KPI objective with Action Plan'),],
        string='Report Type', required=True,
        help='Report Type', default='score')
    year = fields.Selection('_get_year_list', 'Year', default=lambda self: self._get_default_year(), required=True)    
    holiday_type = fields.Selection([
        ('employee', 'By Employee'),
        ('company', 'By Company'),
        ('companyall', 'By All Company'),
        ('department', 'By Department'),
        ('category', 'By Employee Tag'),
        ('emptype', 'By Employee Type')],
        string='Report Mode', required=True, default='employee',
        help='By Employee: Allocation/Request for individual Employee, By Employee Tag: Allocation/Request for group of employees in category')
    
    
    bank_id = fields.Many2one(
        'res.bank',  string='Bank', readonly=False, ondelete="restrict", required=False)
    
    employee_id = fields.Many2one(
        'hr.employee',  domain="['|', ('active', '=', False), ('active', '=', True)]", string='Employee', index=True, readonly=False, ondelete="restrict", default=lambda self: self.env.context.get('default_employee_id') or self.env.user.employee_id)    
    
    category_id = fields.Many2one(
        'hr.employee.category',  string='Employee Tag', help='Category of Employee', readonly=False)
    mode_company_id = fields.Many2one(
        'res.company',  string='Company Mode', readonly=False)
    department_id = fields.Many2one(
        'hr.department',  string='Department', readonly=False)

    
    employee_type = fields.Selection([
        ('staff', 'Staffs'),
        ('worker', 'Workers'),
        ('expatriate', 'Expatriates'),
        ('cstaff', 'C-Staffs'),
        ('cworker', 'C-Workers')],
        string='Employee Type', required=False)
    
    company_all = fields.Selection([
        ('allcompany', 'TEX ZIPPERS (BD) LIMITED')],
        string='All Company', required=False)   
    
    file_data = fields.Binary(readonly=True, attachment=False) 

    
    @staticmethod
    def _get_year_list():
        current_year = datetime.today().year
        year_options = []
        
        for year in range(current_year - 1, current_year + 1):
            year_str = str(year)
            next_year = str(year+1)
            year_label = f'{year_str}-{next_year[2:]}'
            year_options.append((next_year, year_label))
        return year_options     

    @staticmethod
    def _get_default_year():
        current_year = datetime.today().year
        return str(current_year+1)     
    
    @api.depends('employee_id', 'holiday_type')
    def _compute_department_id(self):
        for holiday in self:
            if holiday.employee_id:
                holiday.department_id = holiday.employee_id.department_id
            elif holiday.holiday_type == 'department':
                if not holiday.department_id:
                    holiday.department_id = self.env.user.employee_id.department_id
            else:
                holiday.department_id = False
                
    #@api.depends('holiday_type')
    def _compute_from_holiday_type(self):
        for holiday in self:
            if holiday.holiday_type == 'employee':
                if not holiday.employee_id:
                    holiday.employee_id = self.env.user.employee_id
                holiday.mode_company_id = False
                holiday.category_id = False
                holiday.department_id = False
            elif holiday.holiday_type == 'company':
                if not holiday.mode_company_id:
                    holiday.mode_company_id = self.env.company.id
                holiday.category_id = False
                holiday.department_id = False
                holiday.employee_id = False
            elif holiday.holiday_type == 'department':
                if not holiday.department_id:
                    holiday.department_id = self.env.user.employee_id.department_id
                holiday.employee_id = False
                holiday.mode_company_id = False
                holiday.category_id = False
            elif holiday.holiday_type == 'category':
                if not holiday.category_id:
                    holiday.category_id = self.env.user.employee_id.category_ids
                holiday.employee_id = False
                holiday.mode_company_id = False
                holiday.department_id = False
            #else:
            #    holiday.employee_id = self.env.context.get('default_employee_id') or self.env.user.employee_id
                
    # generate PDF report
    def action_print_report(self):
        if self.report_type:
            if self.holiday_type == "employee":#employee  company department category
                #raise UserError((self.report_type))
                data = {'date_from': self.date_from, 
                        'date_to': self.date_to, 
                        'mode_company_id': False, 
                        'department_id': False, 
                        'category_id': False, 
                        'employee_id': self.employee_id.id,
                        'report_type': self.report_type,
                        'bank_id': False,
                        'company_all': False,
                        'employee_type': False,
                        'year': self.year}

            if self.holiday_type == "company":
                data = {'date_from': self.date_from, 
                        'date_to': self.date_to, 
                        'mode_company_id': self.mode_company_id.id, 
                        'department_id': False, 
                        'category_id': False, 
                        'employee_id': False, 
                        'report_type': self.report_type,
                        'bank_id': False,
                        'company_all': False,
                        'employee_type': False,
                        'year': self.year}

            if self.holiday_type == "department":
                data = {'date_from': self.date_from, 
                        'date_to': self.date_to, 
                        'mode_company_id': False, 
                        'department_id': self.department_id.id, 
                        'category_id': False, 
                        'employee_id': False, 
                        'report_type': self.report_type,
                        'bank_id': False,
                        'company_all': False,
                        'employee_type': False,
                        'year': self.year}

            if self.holiday_type == "category":
                data = {'date_from': self.date_from, 
                        'date_to': self.date_to, 
                        'mode_company_id': False, 
                        'department_id': False, 
                        'category_id': self.category_id.id, 
                        'employee_id': False, 
                        'report_type': self.report_type,
                        'bank_id': False,
                        'company_all': False,
                        'employee_type': False,
                        'year': self.year}
                
            if self.holiday_type == "emptype":
                data = {'date_from': self.date_from, 
                        'date_to': self.date_to, 
                        'mode_company_id': False, 
                        'department_id': False, 
                        'category_id': False, 
                        'employee_id': False, 
                        'report_type': self.report_type,
                        'bank_id': False,
                        'employee_type': self.employee_type,
                        'company_all': False,
                        'year': self.year}              
            if self.holiday_type == "companyall":
                data = {'date_from': self.date_from, 
                        'date_to': self.date_to, 
                        'mode_company_id': False, 
                        'department_id': False, 
                        'category_id': False, 
                        'employee_id': False, 
                        'report_type': self.report_type,
                        'bank_id': False,
                        'employee_type': False,
                        'company_all': self.company_all,
                        'year': self.year}
                
#         return self.env.ref('taps_hr.action_kpi_objective_pdf_report').report_action(self, data=data)
        if self.report_type == 'score':
            return self.env.ref('taps_hr.action_kpi_objective_score_pdf_report').report_action(self, data=data)
        if self.report_type == 'scorequarter':
            return self.env.ref('taps_hr.action_kpi_objective_score_quarter_pdf_report').report_action(self, data=data)
        if self.report_type == 'kpi':
            return self.env.ref('taps_hr.action_kpi_objective_pdf_report').report_action(self, data=data)
        else:
            raise UserError(('This Report are not PDF Format'))

    
    
    def action_generate_xlsx_report(self):
        if self.report_type == 'plan':
            start_time = fields.datetime.now()
            if self.holiday_type == "employee":#employee  company department category
                #raise UserError(('sfefefegegegeeg'))
                data = {'date_from': self.date_from, 
                        'date_to': self.date_to, 
                        'mode_company_id': False, 
                        'department_id': False, 
                        'category_id': False, 
                        'employee_id': self.employee_id.id, 
                        'bank_id': False,
                        'company_all': False,
                        'year': self.year}

            if self.holiday_type == "company":
                data = {'date_from': self.date_from, 
                        'date_to': self.date_to, 
                        'mode_company_id': self.mode_company_id.id, 
                        'department_id': False, 
                        'category_id': False, 
                        'employee_id': False, 
                        'report_type': False,
                        'bank_id': False,
                        'company_all': False,
                        'year': self.year}

            if self.holiday_type == "department":
                data = {'date_from': self.date_from, 
                        'date_to': self.date_to, 
                        'mode_company_id': False, 
                        'department_id': self.department_id.id, 
                        'category_id': False, 
                        'employee_id': False, 
                        'bank_id': False,
                        'company_all': False,
                        'year': self.year}

            if self.holiday_type == "category":
                data = {'date_from': self.date_from, 
                        'date_to': self.date_to, 
                        'mode_company_id': False, 
                        'department_id': False, 
                        'category_id': self.category_id.id, 
                        'employee_id': False, 
                        'bank_id': False,
                        'company_all': False,
                        'year': self.year}

            if self.holiday_type == "emptype":
                data = {'date_from': self.date_from, 
                        'date_to': self.date_to, 
                        'mode_company_id': False, 
                        'department_id': False, 
                        'category_id': False, 
                        'employee_id': False, 
                        'bank_id': False,
                        'employee_type': self.employee_type,
                        'company_all': False,
                        'year': self.year}
            if self.holiday_type == "companyall":
                data = {'date_from': self.date_from, 
                        'date_to': self.date_to, 
                        'mode_company_id': False, 
                        'department_id': False, 
                        'category_id': False, 
                        'employee_id': False, 
                        'bank_id': False,
                        'company_all': self.company_all,
                        'year': self.year}
        else:
            raise UserError(('This Report are not XLSX Format'))
        
        domain = []
#         if data.get('date_from'):
#             domain.append(('date_from', '=', data.get('date_from')))
#         if data.get('date_to'):
#             domain.append(('date_to', '=', data.get('date_to')))
        if data.get('year'):
            deadlines = str(data.get('year') + '-03-31')
            domain.append(('deadline', '=', deadlines))   
        if data.get('mode_company_id'):
            domain.append(('employee_id.company_id.id', '=', data.get('mode_company_id')))
        if data.get('department_id'):
            domain.append(('employee_id.department_id.parent_id.id', '=', data.get('department_id')))
        if data.get('category_id'):
            domain.append(('employee_id.category_ids.id', '=', data.get('category_id')))
        if data.get('employee_id'):
            domain.append(('employee_id.id', '=', data.get('employee_id')))
#         if data.get('bank_id'):
#             domain.append(('employee_id.bank_account_id.bank_id', '=', data.get('bank_id')))
        if data.get('employee_type'):
            if data.get('employee_type')=='staff':
                domain.append(('employee_id.category_ids.id', 'in',(15,21,31)))
            if data.get('employee_type')=='expatriate':
                domain.append(('employee_id.category_ids.id', 'in',(16,22,32)))
            if data.get('employee_type')=='worker':
                domain.append(('employee_id.category_ids.id', 'in',(20,30)))
            if data.get('employee_type')=='cstaff':
                domain.append(('employee_id.category_ids.id', 'in',(26,44,47)))
            if data.get('employee_type')=='cworker':
                domain.append(('employee_id.category_ids.id', 'in',(25,42,43)))
        if data.get('company_all'):
            if data.get('company_all')=='allcompany':
                domain.append(('employee_id.company_id.id', 'in',(1,2,3,4)))                
#         domain.append(('code', '=', 'NET'))
        
        #raise UserError((domain))
        docs1 = self.env['hr.appraisal.goal'].search(domain).sorted(key = 'id', reverse=False)
        # if docs1.employee_id.company_id.id == 1:
        #     docs2 = self.env['hr.appraisal.goal'].search([('id', 'in', (25,27))]).sorted(key = 'id', reverse=False)
        # elif docs1.employee_id.company_id.id == 3:
        #     docs2 = self.env['hr.appraisal.goal'].search([('id', 'in', (26,28))]).sorted(key = 'id', reverse=False)
        # else:
        #     docs2 = self.env['hr.appraisal.goal'].search([('id', 'in', (25,26,27,28))]).sorted(key = 'id', reverse=False)
        
        docs = docs1
        #raise UserError((docs.id))
        datefrom = data.get('date_from')
        dateto = data.get('date_to')
#         bankname = self.bank_id.name
#         categname=[]
#         if self.employee_type =='staff':
#             categname='Staffs'
#         if self.employee_type =='expatriate':
#             categname='Expatriates'
#         if self.employee_type =='worker':
#             categname='Workers'
#         if self.employee_type =='cstaff':
#             categname='C-Staffs'
#         if self.employee_type =='cworker':
#             categname='C-Workers'
            
        
        #raise UserError((datefrom,dateto,bankname,categname))
        report_data = []
        emp_data = []
        slnumber=0
        for edata in docs:
            slnumber = slnumber+1
            emp_data = [
                slnumber,
                edata.name,
                round(edata.baseline,2),
                round(edata.target,2),
                (edata.weight/100),
                "",
                "",
                "",
                edata.employee_id.id,
            ]
            report_data.append(emp_data)     
        emply = docs.mapped('employee_id')
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        # raise UserError((emply))
        for emp in emply:
            
            worksheet = workbook.add_worksheet(('%s - %s' % (emp.pin,emp.name)))
            report_title_style = workbook.add_format({'bold': True, 'font_size': 16, 'bg_color': '#9C5789','right': True, 'border': True, 'font_color':'#FFFFFF'})
            report_column_style = workbook.add_format({'align': 'center','valign': 'vcenter','font_size': 12})
            report_column_style_2 = workbook.add_format({'align': 'left','valign': 'vcenter','font_size': 12, 'left': True, 'top': True, 'right': True, 'bottom': True})
            report_column_style_2.set_text_wrap()
            report_column_style_3 = workbook.add_format({'align': 'left','valign': 'vcenter','font_size': 12, 'left': True, 'top': True, 'right': True, 'bottom': True,'num_format': '0.00%'})
            worksheet.merge_range('A1:H1', 'TEX ZIPPERS (BD) LIMITED', report_title_style)
    
            report_small_title_style = workbook.add_format({'bold': True, 'font_size': 14, 'border': True,'num_format': '0.00%'})
    #         worksheet.write(1, 2, ('From %s to %s' % (datefrom,dateto)), report_small_title_style)
            worksheet.merge_range('A2:H2', (datetime.strptime(str(dateto), '%Y-%m-%d').strftime('%B  %Y')), report_small_title_style)
            worksheet.merge_range('A3:H3', ('KPI objective with Action Plan'), report_small_title_style)
            worksheet.merge_range('A4:E4', ('%s - %s' % (emp.pin,emp.name)), report_title_style)
            worksheet.merge_range('F4:H4', "",report_title_style)
            # worksheet.merge_range('I4:L4', ('Weekly Plan'), report_title_style)
    #         worksheet.write(2, 1, ('TZBD,%s EMPLOYEE %s TRANSFER LIST' % (categname,bankname)), report_small_title_style)
            
            column_product_style = workbook.add_format({'align': 'center','bold': True, 'bg_color': '#00A09D', 'font_size': 12, 'font_color':'#FFFFFF', 'border': True})
            column_received_style = workbook.add_format({'bold': True, 'bg_color': '#A2D374', 'font_size': 12, 'border': True})
            column_issued_style = workbook.add_format({'bold': True, 'bg_color': '#F8715F', 'font_size': 12, 'border': True})
            row_categ_style = workbook.add_format({'border': True})
    
            # set the width od the column
            
            percent_format = workbook.add_format({"num_format": "0%"})
    
            
            worksheet.set_column(0,0,3)
            worksheet.set_column(1,1,50)
            worksheet.set_column(2,3,8)
            worksheet.set_column(4,4,9.44)
            worksheet.set_column(5,7,20)
            
            
            
            worksheet.write(4, 0, 'SL.', column_product_style)
            worksheet.write(4, 1, 'Objectives', column_product_style)        
            worksheet.write(4, 2, 'Baseline', column_product_style)
            worksheet.write(4, 3, 'Target', column_product_style)
            worksheet.write(4, 4, 'Weight', column_product_style)
            worksheet.write(4, 5, 'Last Month Achieved', column_product_style)
            worksheet.write(4, 6, 'Current Monthly Plan', column_product_style)
            worksheet.write(4, 7, 'Actions', column_product_style)
            col = 0
            row=5
            
            grandtotal = 0
    #         grandtotal2 = 0
    #         grandtotal3 = 0
            
            slnumber = 0
            for line in report_data:
                # raise UserError((line[8],emp.id))
                # slnumber=0
                
                
                
                if line[8] == emp.id:
                    slnumber += 1
                    col=0
                    for l in line:
                        if col == 1:
                            etype = l[:1]
                        if col == 0:
                            worksheet.write(row, col, slnumber, report_column_style_2)  
                        elif col == 2:
                            
                            if etype == '%':
                                # raise UserError((etype))
                                ld = l/100
                                worksheet.write(row, col, ld, report_column_style_3)
                            else:
                                # raise UserError((etype))
                                worksheet.write(row, col, l, report_column_style_2)                    
                        elif col == 3:
                            
                            if etype == '%':
                                # raise UserError((etype))
                                ld = l/100
                                worksheet.write(row, col, ld, report_column_style_3)
                            else:
                                # raise UserError((etype))
                                worksheet.write(row, col, l, report_column_style_2)
                        elif col==4:
                            grandtotal = grandtotal+l
                            # format = workbook.add_format({'num_format': num_formats})
                            worksheet.write(row, col, l, report_column_style_3)
                        elif col==8:
                            break
                        else:
                            worksheet.write(row, col, l, report_column_style_2)
                        col+=1
                    row+=1
                    
            
                    #worksheet.write(4, 0, 'SL.', column_product_style)
                    #raise UserError((row+1))
                    worksheet.write(row, 0, '', report_small_title_style)
                    worksheet.write(row, 1, 'Grand Total', report_small_title_style)
                    worksheet.write(row, 2, '', report_small_title_style)
                    worksheet.write(row, 3, '', report_small_title_style)
                    worksheet.write(row, 4, round(grandtotal,2), report_small_title_style)
                    worksheet.write(row, 5, '', report_small_title_style)
                    worksheet.write(row, 6, '', report_small_title_style)
                    worksheet.write(row, 7, '', report_small_title_style)
                    #raise UserError((datefrom,dateto,bankname,categname))
            
        workbook.close()
        output.seek(0)
        xlsx_data = output.getvalue()
        #raise UserError(('sfrgr'))
        
        self.file_data = base64.encodebytes(xlsx_data)
        end_time = fields.datetime.now()
        
        _logger.info("\n\nTOTAL PRINTING TIME IS : %s \n" % (end_time - start_time))
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/?model={}&id={}&field=file_data&filename={}&download=true'.format(self._name, self.id, ('%s - KPI objective with Action Plan'% (emp.department_id.parent_id.name))),
            'target': 'self',
        }    


    

class KpiScoreReportPDF(models.AbstractModel):
    _name = 'report.taps_hr.kpi_objective_score_pdf_template'
    _description = 'KPI Objective Score Report Template'     

    def _get_report_values(self, docids, data=None):
        domain = []
        
#         if data.get('bank_id')==False:
#             domain.append(('code', '=', data.get('report_type')))
#         if data.get('date_from'):
#             domain.append(('date_from', '>=', data.get('date_from')))
#         if data.get('date_to'):
#             domain.append(('date_to', '<=', data.get('date_to')))
        if data.get('year'):
            deadlines = str(data.get('year') + '-03-31')
            domain.append(('deadline', '=', deadlines))
        if data.get('mode_company_id'):
            #str = re.sub("[^0-9]","",data.get('mode_company_id'))
            domain.append(('employee_id.company_id.id', '=', data.get('mode_company_id')))
        if data.get('department_id'):
            #str = re.sub("[^0-9]","",data.get('department_id'))
            domain.append(('employee_id.department_id.id', '=', data.get('department_id')))
        if data.get('category_id'):
            #str = re.sub("[^0-9]","",data.get('category_id'))
            domain.append(('employee_id.category_ids.id', '=', data.get('category_id')))
        if data.get('employee_id'):
            #str = re.sub("[^0-9]","",data.get('employee_id'))
            domain.append(('employee_id.id', '=', data.get('employee_id')))
#         if data.get('bank_id'):
#             #str = re.sub("[^0-9]","",data.get('employee_id'))
#             domain.append(('employee_id.bank_account_id.bank_id', '=', data.get('bank_id')))
        if data.get('employee_type'):
            if data.get('employee_type')=='staff':
                domain.append(('employee_id.category_ids.id', 'in',(15,21,31)))
            if data.get('employee_type')=='expatriate':
                domain.append(('employee_id.category_ids.id', 'in',(16,22,32)))
            if data.get('employee_type')=='worker':
                domain.append(('employee_id.category_ids.id', 'in',(20,30)))
            if data.get('employee_type')=='cstaff':
                domain.append(('employee_id.category_ids.id', 'in',(26,44,47)))
            if data.get('employee_type')=='cworker':
                domain.append(('employee_id.category_ids.id', 'in',(25,42,43)))
        if data.get('company_all'):
            if data.get('company_all')=='allcompany':
                domain.append(('employee_id.company_id.id', 'in',(1,2,3,4)))                
#         domain.append( ('id', 'in', (25,26,27,28)))        
        
        
        
        docs1 = self.env['hr.appraisal.goal'].search(domain).sorted(key = 'id', reverse=False)
        if docs1.employee_id.company_id.id == 1:
            docs2 = self.env['hr.appraisal.goal'].search([('id', 'in', (25,27)), ('deadline', '=', deadlines)]).sorted(key = 'id', reverse=False)
        elif docs1.employee_id.company_id.id == 3:
            docs2 = self.env['hr.appraisal.goal'].search([('id', 'in', (26,28)), ('deadline', '=', deadlines)]).sorted(key = 'id', reverse=False)
        else:
            docs2 = self.env['hr.appraisal.goal'].search([('id', 'in', (25,26,27,28)), ('deadline', '=', deadlines)]).sorted(key = 'id', reverse=False)
        
        docs = docs2 | docs1
#         raise UserError((docs.id))
        month = docs.mapped('month')[1:]
        mm = 'Month'
        for m in month:
            if m == 'apr':
                mm = 'April'
            elif m == 'may':
                mm = 'May'
            elif m == 'jun':
                mm = 'Jun'
            elif m == 'jul':
                mm = 'July'
            elif m == 'aug':
                mm = 'August'
            elif m == 'sep':
                mm = 'September'
            elif m == 'oct':
                mm = 'October'
            elif m == 'nov':
                mm = 'November'
            elif m == 'dec':
                mm = 'December'
            elif m == 'jan':
                mm = 'January'
            elif m == 'feb':
                mm = 'February'
            elif m == 'mar':
                mm = 'March'
        weight = 0
        apr = 0
        may = 0
        jun = 0
        jul = 0
        aug = 0
        sep = 0
        oct = 0
        nov = 0
        dec = 0
        jan = 0
        feb = 0
        mar = 0
        ytd = 0
        for de in docs1:
            weight = weight + de.weight
            apr = apr + de.apr
            may = may + de.may
            jun = jun + de.jun
            jul = jul + de.jul
            aug = aug + de.aug
            sep = sep + de.sep
            oct = oct + de.oct
            nov = nov + de.nov
            dec = dec + de.dec
            jan = jan + de.jan
            feb = feb + de.feb
            mar = mar + de.mar
            ytd = ytd + de.y_ytd
            
        common_data = [
            data.get('report_type'),
            mm,
            weight,
            apr,
            may,
            jun,
            jul,
            aug,
            sep,
            oct,
            nov,
            dec,
            jan,
            feb,
            mar,
            ytd,
#             round(otTotal),
            data.get('date_from'),
            data.get('date_to'),
        ]
        common_data.append(common_data)
#         raise UserError((common_data[1]))
#         raise UserError((mm))
        return {
            'doc_ids': docs.ids,
            'doc_model': 'hr.appraisal.goal',
            'docs': docs,
            'datas': common_data,
#             'alldays': all_datelist
        }

class KpiScoreQuaterReportPDF(models.AbstractModel):
    _name = 'report.taps_hr.kpi_objective_score_quarter_pdf_template'
    _description = 'KPI Objective Score Quarterly Report Template'     

    def _get_report_values(self, docids, data=None):
        domain = []
        
#         if data.get('bank_id')==False:
#             domain.append(('code', '=', data.get('report_type')))
#         if data.get('date_from'):
#             domain.append(('date_from', '>=', data.get('date_from')))
#         if data.get('date_to'):
#             domain.append(('date_to', '<=', data.get('date_to')))
        if data.get('year'):
            deadlines = str(data.get('year') + '-03-31')
            domain.append(('deadline', '=', deadlines))
        if data.get('mode_company_id'):
            #str = re.sub("[^0-9]","",data.get('mode_company_id'))
            domain.append(('employee_id.company_id.id', '=', data.get('mode_company_id')))
        if data.get('department_id'):
            #str = re.sub("[^0-9]","",data.get('department_id'))
            domain.append(('employee_id.department_id.id', '=', data.get('department_id')))
        if data.get('category_id'):
            #str = re.sub("[^0-9]","",data.get('category_id'))
            domain.append(('employee_id.category_ids.id', '=', data.get('category_id')))
        if data.get('employee_id'):
            #str = re.sub("[^0-9]","",data.get('employee_id'))
            domain.append(('employee_id.id', '=', data.get('employee_id')))
#         if data.get('bank_id'):
#             #str = re.sub("[^0-9]","",data.get('employee_id'))
#             domain.append(('employee_id.bank_account_id.bank_id', '=', data.get('bank_id')))
        if data.get('employee_type'):
            if data.get('employee_type')=='staff':
                domain.append(('employee_id.category_ids.id', 'in',(15,21,31)))
            if data.get('employee_type')=='expatriate':
                domain.append(('employee_id.category_ids.id', 'in',(16,22,32)))
            if data.get('employee_type')=='worker':
                domain.append(('employee_id.category_ids.id', 'in',(20,30)))
            if data.get('employee_type')=='cstaff':
                domain.append(('employee_id.category_ids.id', 'in',(26,44,47)))
            if data.get('employee_type')=='cworker':
                domain.append(('employee_id.category_ids.id', 'in',(25,42,43)))
        if data.get('company_all'):
            if data.get('company_all')=='allcompany':
                domain.append(('employee_id.company_id.id', 'in',(1,2,3,4)))                
#         domain.append( ('id', 'in', (25,26,27,28)))        
        
        
        
        docs1 = self.env['hr.appraisal.goal'].search(domain).sorted(key = 'id', reverse=False)
        if docs1.employee_id.company_id.id == 1:
            docs2 = self.env['hr.appraisal.goal'].search([('id', 'in', (25,27)), ('deadline', '=', deadlines)]).sorted(key = 'id', reverse=False)
        elif docs1.employee_id.company_id.id == 3:
            docs2 = self.env['hr.appraisal.goal'].search([('id', 'in', (26,28)), ('deadline', '=', deadlines)]).sorted(key = 'id', reverse=False)
        else:
            docs2 = self.env['hr.appraisal.goal'].search([('id', 'in', (25,26,27,28)), ('deadline', '=', deadlines)]).sorted(key = 'id', reverse=False)
        
        docs = docs2 | docs1
#         raise UserError((docs.id))
        month = docs.mapped('month')[1:]
        mm = 'Month'
        for m in month:
            if m == 'apr':
                mm = 'April'
            elif m == 'may':
                mm = 'May'
            elif m == 'jun':
                mm = 'Jun'
            elif m == 'jul':
                mm = 'July'
            elif m == 'aug':
                mm = 'August'
            elif m == 'sep':
                mm = 'September'
            elif m == 'oct':
                mm = 'October'
            elif m == 'nov':
                mm = 'November'
            elif m == 'dec':
                mm = 'December'
            elif m == 'jan':
                mm = 'January'
            elif m == 'feb':
                mm = 'February'
            elif m == 'mar':
                mm = 'March'
        weight = 0
        apr = 0
        may = 0
        jun = 0
        q_1_ytd = 0
        jul = 0
        aug = 0
        sep = 0
        q_2_ytd = 0
        oct = 0
        nov = 0
        dec = 0
        q_3_ytd = 0
        jan = 0
        feb = 0
        mar = 0
        q_4_ytd = 0  
        ytd = 0
        for de in docs1:
            weight = weight + de.weight
            apr = apr + de.apr
            may = may + de.may
            jun = jun + de.jun
            q_1_ytd = q_1_ytd + de.q_1_ytd
            jul = jul + de.jul
            aug = aug + de.aug
            sep = sep + de.sep
            q_2_ytd = q_2_ytd + de.q_2_ytd
            oct = oct + de.oct
            nov = nov + de.nov
            dec = dec + de.dec
            q_3_ytd = q_3_ytd + de.q_3_ytd
            jan = jan + de.jan
            feb = feb + de.feb
            mar = mar + de.mar
            q_4_ytd = q_4_ytd + de.q_4_ytd
            ytd = ytd + de.y_ytd
            
        common_data = [
            data.get('report_type'),
            mm,
            weight,
            apr,
            may,
            jun,
            jul,
            aug,
            sep,
            oct,
            nov,
            dec,
            jan,
            feb,
            mar,
            ytd,
#             round(otTotal),
            data.get('date_from'),
            data.get('date_to'),
            q_1_ytd,
            q_2_ytd,
            q_3_ytd,
            q_4_ytd,
        ]
        common_data.append(common_data)
#         raise UserError((common_data[1]))
#         raise UserError((mm))
        return {
            'doc_ids': docs.ids,
            'doc_model': 'hr.appraisal.goal',
            'docs': docs,
            'datas': common_data,
#             'alldays': all_datelist
        }

class KpiReportPDF(models.AbstractModel):
    _name = 'report.taps_hr.kpi_objective_pdf_template'
    _description = 'KPI Objective Report Template'     

    def _get_report_values(self, docids, data=None):
        domain = []
        
#         if data.get('bank_id')==False:
#             domain.append(('code', '=', data.get('report_type')))
#         if data.get('date_from'):
#             domain.append(('date_from', '>=', data.get('date_from')))
#         if data.get('date_to'):
#             domain.append(('date_to', '<=', data.get('date_to')))
        if data.get('year'):
            deadlines = str(data.get('year') + '-03-31')
            domain.append(('deadline', '=', deadlines))
        if data.get('mode_company_id'):
            #str = re.sub("[^0-9]","",data.get('mode_company_id'))
            domain.append(('employee_id.company_id.id', '=', data.get('mode_company_id')))
        if data.get('department_id'):
            #str = re.sub("[^0-9]","",data.get('department_id'))
            domain.append(('employee_id.department_id.id', '=', data.get('department_id')))
        if data.get('category_id'):
            #str = re.sub("[^0-9]","",data.get('category_id'))
            domain.append(('employee_id.category_ids.id', '=', data.get('category_id')))
        if data.get('employee_id'):
            #str = re.sub("[^0-9]","",data.get('employee_id'))
            domain.append(('employee_id.id', '=', data.get('employee_id')))
#         if data.get('bank_id'):
#             #str = re.sub("[^0-9]","",data.get('employee_id'))
#             domain.append(('employee_id.bank_account_id.bank_id', '=', data.get('bank_id')))
        if data.get('employee_type'):
            if data.get('employee_type')=='staff':
                domain.append(('employee_id.category_ids.id', 'in',(15,21,31)))
            if data.get('employee_type')=='expatriate':
                domain.append(('employee_id.category_ids.id', 'in',(16,22,32)))
            if data.get('employee_type')=='worker':
                domain.append(('employee_id.category_ids.id', 'in',(20,30)))
            if data.get('employee_type')=='cstaff':
                domain.append(('employee_id.category_ids.id', 'in',(26,44,47)))
            if data.get('employee_type')=='cworker':
                domain.append(('employee_id.category_ids.id', 'in',(25,42,43)))
        if data.get('company_all'):
            if data.get('company_all')=='allcompany':
                domain.append(('employee_id.company_id.id', 'in',(1,2,3,4)))                
#         domain.append( ('id', 'in', (25,26,27,28)))        
        
        
        
        docs1 = self.env['hr.appraisal.goal'].search(domain).sorted(key = 'id', reverse=False)
        if docs1.employee_id.company_id.id == 1:
            docs2 = self.env['hr.appraisal.goal'].search([('id', 'in', (25,27)), ('deadline', '=', deadlines)]).sorted(key = 'id', reverse=False)
        elif docs1.employee_id.company_id.id == 3:
            docs2 = self.env['hr.appraisal.goal'].search([('id', 'in', (26,28)), ('deadline', '=', deadlines)]).sorted(key = 'id', reverse=False)
        else:
            docs2 = self.env['hr.appraisal.goal'].search([('id', 'in', (25,26,27,28)), ('deadline', '=', deadlines)]).sorted(key = 'id', reverse=False)
        
        docs = docs2 | docs1
#         raise UserError((docs.id))
        month = docs.mapped('month')[1:]
        mm = 'Month'
        for m in month:
            if m == 'apr':
                mm = 'April'
            elif m == 'may':
                mm = 'May'
            elif m == 'jun':
                mm = 'Jun'
            elif m == 'jul':
                mm = 'July'
            elif m == 'aug':
                mm = 'August'
            elif m == 'sep':
                mm = 'September'
            elif m == 'oct':
                mm = 'October'
            elif m == 'nov':
                mm = 'November'
            elif m == 'dec':
                mm = 'December'
            elif m == 'jan':
                mm = 'January'
            elif m == 'feb':
                mm = 'February'
            elif m == 'mar':
                mm = 'March'
        weight = 0
        apr = 0
        may = 0
        jun = 0
        jul = 0
        aug = 0
        sep = 0
        oct = 0
        nov = 0
        dec = 0
        jan = 0
        feb = 0
        mar = 0
        ytd = 0
        for de in docs1:
            weight = weight + de.weight
            apr = apr + de.apr
            may = may + de.may
            jun = jun + de.jun
            jul = jul + de.jul
            aug = aug + de.aug
            sep = sep + de.sep
            oct = oct + de.oct
            nov = nov + de.nov
            dec = dec + de.dec
            jan = jan + de.jan
            feb = feb + de.feb
            mar = mar + de.mar
            ytd = ytd + de.y_ytd
            
        common_data = [
            data.get('report_type'),
            mm,
            weight,
            apr,
            may,
            jun,
            jul,
            aug,
            sep,
            oct,
            nov,
            dec,
            jan,
            feb,
            mar,
            ytd,
#             round(otTotal),
            data.get('date_from'),
            data.get('date_to'),
        ]
        common_data.append(common_data)
#         raise UserError((common_data[1]))
#         raise UserError((mm))
        return {
            'doc_ids': docs.ids,
            'doc_model': 'hr.appraisal.goal',
            'docs': docs1,
            'datas': common_data,
#             'alldays': all_datelist
        }
