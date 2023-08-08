# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
import logging

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class HrAppraisal(models.Model):
    _inherit = "hr.appraisal"
    _description = "Employee Appraisal"
    _order = 'employee_id'


    ytd_weightage_acvd = fields.Float(string='YTD Weightage ACVD', compute='_compute_ytd_weightage_acvd')
    total_weightage = fields.Float(string='Weightage', store=True, copy=True, default="0", compute='_compute_ytd_weightage_acvd')
    manager_ids = fields.Many2many('hr.employee', 'appraisal_manager_rel', 'hr_appraisal_id', domain=[])
    
    # @api.multi
    def action_create_meeting_event(self):
        view_id = self.env.ref('taps_hr.view_meeting_event_wizard_form').id
        return {
            'name': 'Create Meeting Event',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'meeting.event.wizard',
            'views': [(view_id, 'form')],
            'target': 'new',
            # 'context': {'default_meeting_date': self.date_close},  # Pass the meeting_date to the wizard
        }    
    # def action_create_meeting_events(self, meeting_date=False):
    #     # raise UserError((self))
    #     for appraisal in self:
    #         # employees = appraisal.employee_id
    #         # if not employees:
    #         #     continue
    #         if not meeting_date:
    #             raise UserError(('Please set a meeting date before call the meeting event button.'))
            
    
    #         event_vals = {
    #             'name': 'Appraisal Meeting',
    #             'start': meeting_date,
    #             'stop': meeting_date,
    #             'start_date': meeting_date,
    #             'stop_date': meeting_date,
    #             'user_id': appraisal.employee_id.user_id.id,
    #         }
    #         meeting = self.env['calendar.event'].create(event_vals)
    #         # raise UserError((self.employee_id))
    #         appraisal.meeting_id = meeting.id
    #         appraisal.date_final_interview = meeting_date

    #     # return True
    def _compute_ytd_weightage_acvd(self):
        for appraisal in self:
            app_goal = self.env['hr.appraisal.goal'].search([('employee_id', '=', appraisal.employee_id.id), ('deadline', '=', appraisal.date_close)])
            ytd = 0
            weight = 0
            ytd = sum(app_goal.mapped('y_ytd'))
            weight = sum(app_goal.mapped('weight'))
            appraisal.ytd_weightage_acvd = ytd
            appraisal.total_weightage = weight

    def action_open_goals(self):
        self.ensure_one()
        return {
            'name': _('%s Goals') % self.employee_id.name,
            'view_mode': 'kanban,tree,form',
            'res_model': 'hr.appraisal.goal',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': [('employee_id', '=', self.employee_id.id), ('deadline', '=', self.date_close)],
            'context': {'default_employee_id': self.employee_id.id},
        }
    def action_done(self):
        current_date = datetime.date.today()
        self.activity_feedback(['mail.mail_activity_data_meeting', 'mail.mail_activity_data_todo'])
        self.write({'state': 'done'})
        for appraisal in self:
            appraisal.employee_id.write({
                'last_appraisal_id': appraisal.id,
                'last_appraisal_date': appraisal.date_close,#current_date
                'next_appraisal_date': False})
            
class MeetingEventWizard(models.TransientModel):
    _name = 'meeting.event.wizard'
    _description = 'Meeting Event Wizard'

    meeting_date = fields.Datetime(string='Meeting Date', required=True)
    # Add more fields if needed for your wizard

    def create_event_and_appraisal(self):
        active_ids = self._context.get('active_ids', [])
        if not active_ids:
            return

        meeting_date = self.meeting_date  # Assuming you have a field 'meeting_date' in the wizard

        # Call the action_create_meeting_event method for each hr.appraisal record
        hr_appraisal = self.env['hr.appraisal'].browse(active_ids)
        user_id = self.env.user.id
        partner_ids = [appraisal.employee_id.address_home_id.id for appraisal in hr_appraisal]
        # raise UserError(([appraisal.employee_id.address_home_id.id for appraisal in hr_appraisal]))
        # for appraisal in hr_appraisal:
            # mt.action_create_meeting_events(meeting_date)
        event_vals = {
            'name': 'Appraisal Meeting',
            'start': meeting_date,
            'stop': meeting_date,
            'start_date': meeting_date,
            'stop_date': meeting_date,
            'user_id': user_id,
            'partner_ids': [(6, 0, partner_ids)],
        }
        meeting = self.env['calendar.event'].create(event_vals)
        # raise UserError((self.employee_id))
        for appraisal in hr_appraisal:
            appraisal.meeting_id = meeting.id
            appraisal.date_final_interview = meeting_date
            meeting_activity_type = self.env['mail.activity.type'].search([('category', '=', 'meeting')], limit=1)
    
            # Create an activity note for each partner in partner_ids
        # for appraisal in hr_appraisal:
            
            activity_vals = {
                'activity_type_id': meeting_activity_type.id,  # You may need to adjust this activity type ID
                'user_id': appraisal.employee_id.user_id.id,
                'summary': 'Appraisal Meeting',
                'note': f'Appraisal Meeting with {appraisal.employee_id.name}',
                'res_model_id': self.env['ir.model']._get('hr.appraisal').id,
                'res_id': appraisal.id,
                'date_deadline': meeting_date,  # Associate all partners with this activity deadline
                'calendar_event_id': meeting.id,
            }
            activity = self.env['mail.activity'].create(activity_vals)
    
                # # Send email notification
            # template_id = self.env.ref('your_module.your_email_template_id')
            # if template_id:
            #             template_id.send_mail(activity.id, force_send=True, email_values={'calendar_event_id': meeting.id})

        return {'type': 'ir.actions.act_window_close'} 

class CalendarEvent(models.Model):
    """ Model for Calendar Event """
    _inherit = 'calendar.event'

    @api.model_create_multi
    def create(self, vals_list):
        events = super().create(vals_list)
        
        # for event in events:
        #     if event.res_model == 'hr.appraisal':
        #         appraisal = self.env['hr.appraisal'].browse(event.res_id)
        #         # raise UserError((appraisal))
        #         if appraisal.exists():
        #             appraisal.write({
        #                 'meeting_id': event.id,
        #                 'date_final_interview': event.start_date if event.allday else event.start
        #             })
        return events
