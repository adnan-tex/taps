import base64

from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.addons.hr_payroll.models.browsable_object import BrowsableObject, InputLine, WorkedDays, Payslips, ResultRules
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_round, date_utils
from odoo.tools.misc import format_date
from odoo.tools.safe_eval import safe_eval


class IncrementPromotion(models.Model):
    _name = 'increment.promotion'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _description = 'Increment Promotion'
    
    name = fields.Char('Code', store=True,required=True, readonly=True, index=True, copy=False, tracking=True, default='IP')
    increment_month = fields.Date('Increment Month', store=True, tracking=True, default=date.today().strftime('%Y-%m-01'))
    increment_line = fields.One2many('increment.promotion.line', 'increment_id', string='Increment Lines',tracking=True, store=True, required=True)
    state = fields.Selection([
    ('draft', 'To Submit'),
    ('submit', 'Submitted'),
    ('approved', 'Approved'),
    ('refused', 'Refused')], string='Status', copy=False, 
        index=True, readonly=True, store=True, default='draft', tracking=True, help="Status of the Increment")
    

    
    def button_approve(self, force=False):
        if self.increment_line:
            for app in self.increment_line:
                elist = self.env['hr.employee'].search([('id','=',app.employee_id.id)])
                conlist = self.env['hr.contract'].search([('employee_id','=',app.employee_id.id)])
                if app.new_job_id:
                    elist[-1].write({'job_id': app.new_job_id.id})
                    conlist[-1].write({'job_id': app.new_job_id.id})
                if app.new_grade:
                    conlist[-1].write({'structure_type_id': app.new_grade.id})
                if app.increment_amount > 0:
                    conlist[-1].write({'wage': app.employee_id.contract_id.wage + app.increment_amount})
                if app.ot_type == "true":
                    elist[-1].write({'isOverTime': True})
                if app.ot_type == "false":
                    elist[-1].write({'isOverTime': False})
                
                    
                    
                    
                    
        self.write({'state': 'approved'})
        return {}

    def button_confirm(self):
        for order in self:
            if order.state not in ['draft', 'submit']:
                continue
            order.write({'state': 'submit'})
        return True     
    
    def button_draft(self):
        self.write({'state': 'draft'})
        return {}    
    
    def button_cancel(self):
        self.write({'state': 'refused'})        
    
    @api.model
    def create(self, vals):
        if vals.get('name', 'IP') == 'IP':
            vals['name'] = self.env['ir.sequence'].next_by_code('increment.code')
        return super(IncrementPromotion, self).create(vals)


class IncrementPromotionLine(models.Model):
    _name = 'increment.promotion.line'
    _description = 'Increment Promotion Line'
    
    increment_id = fields.Many2one('increment.promotion', string='Increment Reference', index=True, required=True, ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, store=True)
    job_id = fields.Many2one('hr.job', 'Position', store=True, readonly=True, compute='_compute_job_id')
    new_job_id = fields.Many2one('hr.job', 'New Job Position', tracking=True, store=True)
    grade = fields.Many2one('hr.payroll.structure.type', 'Grade', store=True, readonly=True, compute='_compute_job_id')
    new_grade = fields.Many2one('hr.payroll.structure.type', 'New Grade', tracking=True, store=True)
    old_ot_type = fields.Boolean("old OT Type", readonly=False, store=True, compute='_compute_job_id')
    ot_type = fields.Selection([('true', "Yes"),('false', "No")], compute='onchange_ot_type', string="OT Type", store=True, tracking=True, readonly=False, required=True)
    increment_percent = fields.Float(string='Increment Percent',readonly=False, compute='calculate_amount', tracking=True, store=True)
    increment_amount = fields.Float(string='Increment Amount',readonly=False, compute='calculate_percent', tracking=True, store=True)
    
    @api.depends('employee_id')
    def _compute_job_id(self):
        for line in self.filtered('employee_id'):
            line.job_id = line.employee_id.job_id.id
            line.grade = line.employee_id.contract_id.structure_type_id
            line.old_ot_type = line.employee_id.isOverTime
            
    
    @api.depends('employee_id')
    def onchange_ot_type(self):
        for ot in self:
            if ot.employee_id:
                ottype = ot.employee_id.isOverTime
                if ottype:
                    #raise UserError(('sfefefe'))
                    ot.ot_type = 'true'
                else:
                    ot.ot_type = 'false'
            #return ot.ot_type
#             ot.department_id = ot.employee_id.department_id
    
    @api.onchange('employee_id','increment_percent')
    def calculate_amount(self):
        for inc in self:
            gross = inc.employee_id.contract_id.wage
            if inc.increment_percent:
                inc.increment_amount = (gross*inc.increment_percent)/100
            
    @api.onchange('employee_id','increment_amount')
    def calculate_percent(self):
        for inc in self:
            gross = inc.employee_id.contract_id.wage
            if inc.increment_amount:
                inc.increment_percent = (100*inc.increment_amount)/gross            
            
#     @api.onchange('employee_id')
#     def onchange_ot_type(self):
# #         self.ot_type = ''
#         for ot in self:
#             if ot.employee_id.isOverTime == False:
#                 ot.ot_type = 'False'
#             if ot.employee_id.isOverTime == True:
#                 ot.ot_type = 'True'