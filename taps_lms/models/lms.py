from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import timedelta
from odoo.tools.misc import get_lang
import logging
from odoo.tools.profiler import profile

logger = logging.getLogger("*___LMS___*")
_logger = logging.getLogger(__name__)


class Course(models.Model):
    _name = 'lms.course'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Training Courses'
    _rec_name = 'title_ids'

    name = fields.Char(string="Course Number", required=True, index=True, copy=False, readonly=True, default=_('New'))
    criteria_id = fields.Many2one('lms.criteria', required=True, string='Criteria') 
    title_ids = fields.Many2one('lms.title', string='Title', required=True, domain="['|', ('criteria_id', '=', False), ('criteria_id', '=', criteria_id)]")       
    description = fields.Text('Content', related="title_ids.description",help='Add content description here...')
    responsible_id = fields.Many2one('res.users', ondelete='set null', string="Responsible", index=True, tracking=True)
    session_ids = fields.One2many('lms.session', 'course_id', string="Sessions")
    state = fields.Selection([('draft', 'Draft'), ('submitted', 'Submitted'), ('in_progress', 'In Progress'), ('completed', 'Completed'), ('cancel', 'Cancel')
                              ], string='Status', readonly=False, tracking=True, default='draft', copy=False)
    course_date = fields.Date('Course date', required=True, default=fields.Date.today())

    def action_submit(self):
        self.state = 'submitted'
        users = self.env.ref('taps_lms.group_course_approval').users
        for user in users:
            self.activity_schedule('taps_lms.mail_act_course_approval', user_id=user.id, note=f'Please Approve Training course {self.name}')

    def name_get(self):
        result = []
        for record in self:
            name = f"[{record.name}] {record.title_ids.name}"
            result.append((record.id, name))
        return result

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        if not args:
            args = []
        if name:
            course_ids = self._search([('name', operator, name)] + args, limit=limit, access_rights_uid=name_get_uid)
            if not course_ids:
                course_ids = self._search([('title_ids', operator, name)] + args, limit=limit, access_rights_uid=name_get_uid)
        else:
            course_ids = self._search(args, limit=limit, access_rights_uid=name_get_uid)
        return course_ids #models.lazy_name_get(self.browse(course_ids).with_user(name_get_uid))

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            course_date = vals.get('course_date')
            vals['name'] = self.env['ir.sequence'].next_by_code('lms.course', sequence_date=course_date)
        return super(Course, self).create(vals)

    def action_validate(self):
        for record in self:
            logger.info(f"Course {record.title_ids} state moved to In progress by {self.env.user.name}")
            record.write({'state': 'in_progress'})
            activity_id = self.env['mail.activity'].search([('res_id', '=', self.id), ('user_id', '=', self.env.user.id),
                                                            ('activity_type_id', '=', self.env.ref('taps_lms.mail_act_course_approval').id)])
            activity_id.action_feedback(feedback='Approved')
            other_activity_ids = self.env['mail.activity'].search(
                [('res_id', '=', self.id), ('activity_type_id', '=', self.env.ref('taps_lms.mail_act_course_approval').id)])
            other_activity_ids.unlink()

    def action_completed(self):
        for record in self:
            record.write({'state': 'completed'})
            return {
                'effect': {
                    'fadeout': 'slow',
                    'message': 'Course Completed',
                    'type': 'rainbow_man',
                    'img_url': 'taps_lms/static/img/success.png'
                }
            }

    def action_cancel(self):
        for record in self:
            logger.error(f"Course {record.title_ids} state moved to Cancelled by {self.env.user.name}")
            record.write({'state': 'cancel'})

    def copy(self, default=None):
        default = dict(default or {})

        copied_count = self.search_count(
            [(_('title_ids', '=like', u"Copy of {}%").format(self.title_ids))])
        if not copied_count:
            new_name = u"Copy of {}".format(self.title_ids)
        else:
            new_name = u"Copy of {} ({})".format(self.title_ids, copied_count)

        default['title_ids'] = new_name
        return super(Course, self).copy(default)

    _sql_constraints = [
        ('title_ids_unique',
         'unique(criteria_id,title_ids)',
         'Criteria and Title name should be unique'),
    ]


class Session(models.Model):
    _name = 'lms.session'
    _description = "Training Sessions"
    _inherit = ['mail.thread']
    _rec_name = 'course_id'    

    def get_default_duration(self):
        ICP = self.env['ir.config_parameter'].sudo()
        default_duration = ICP.get_param('taps_lms.session_duration')
        return default_duration

    def get_default_seats(self):
        ICP = self.env['ir.config_parameter'].sudo()
        default_seats = ICP.get_param('taps_lms.session_allowed_seats')
        return default_seats

    # @api.onchange('course_id', 'instructor_id')
    # def _get_instructor_domain(self):
    #     # raise UserError((self.course_id.responsible_id.partner_id.id))
    #     return {'domain': {'instructor_id': [('user_id', '=', self.course_id.responsible_id.id)]}}
    code = fields.Char(string="Number", required=True, index=True, copy=False, readonly=True, default=_('New'))
    name = fields.Many2one('lms.session.venue', string='Venue')
    start_date = fields.Datetime(string="Plan Date",default=fields.datetime.today())
    duration = fields.Float(digits=(6, 2), help="Duration in hours", default=get_default_duration)
    end_date = fields.Datetime(string="End Date", store=True, compute='_get_end_date', inverse='_set_end_date')
    seats = fields.Integer(string="Number of seats", default=get_default_seats)
    instructor_id = fields.Many2one('hr.employee', string="Facilitator")    
    country_id = fields.Many2one('res.country', related='instructor_id.country_id')
    course_id = fields.Many2one('lms.course', ondelete='cascade', string="Course", required=True)
    attendee_ids = fields.Many2many('hr.employee', string="Particpants")
    taken_seats = fields.Float(string="Taken seats", compute='_taken_seats')
    active = fields.Boolean(string='Active', default=True)
    attendees_count = fields.Integer(
        string="Attendees count", compute='_get_attendees_count', store=True)
    color = fields.Integer()
    email_sent = fields.Boolean('Email Sent', default=False)
    image_1920 = fields.Image("Image")
    attendance_ids = fields.One2many('lms.session.attendance', 'session_id', string="Particpants Attendance")

    # def _query(self, fields='', from_clause='', outer=''):
    #     select_ = '''
    #         c.id as id,
    #         c.id as contract_id,
    #         e.id as employee_id,
    #         e.company_id as company_id,
    #         e.departure_reason as departure_reason,
    #         e.department_id as department_id,
    #         c.wage AS wage,
    #         CASE WHEN serie = start.contract_start THEN 1 ELSE 0 END as count_new_employee,
    #         CASE WHEN date_part('month', exit.contract_end) = date_part('month', serie) AND date_part('year', exit.contract_end) = date_part('year', serie) THEN 1 ELSE 0 END as count_employee_exit,
    #         c.date_start,
    #         c.date_end,
    #         exit.contract_end as date_end_contract,
    #         start.contract_start,
    #         CASE
    #             WHEN date_part('month', c.date_start) = date_part('month', serie) AND date_part('year', c.date_start) = date_part('year', serie)
    #                 THEN (31 - LEAST(date_part('day', c.date_start), 30)) / 30
    #             WHEN c.date_end IS NULL THEN 1
    #             WHEN date_part('month', c.date_end) = date_part('month', serie) AND date_part('year', c.date_end) = date_part('year', serie)
    #                 THEN (LEAST(date_part('day', c.date_end), 30) / 30)
    #             ELSE 1 END as age_sum,
    #         serie::DATE as date,
    #         EXTRACT(EPOCH FROM serie)/2628028.8 AS start_date_months, -- 2628028.8 = 3600 * 24 * 30.417 (30.417 is the mean number of days in a month)
    #         CASE
    #             WHEN c.date_end IS NOT NULL AND date_part('month', c.date_end) = date_part('month', serie) AND date_part('year', c.date_end) = date_part('year', serie) THEN
    #                 EXTRACT(EPOCH FROM (c.date_end))/2628028.8
    #             ELSE
    #                 EXTRACT(EPOCH FROM (date_trunc('month', serie) + interval '1 month' - interval '1 day'))/2628028.8
    #             END AS end_date_months

    #         %s
    #     ''' % fields

    #     from_ = """
    #             (SELECT age(COALESCE(date_end, current_date), date_start) as age, * FROM hr_contract WHERE state != 'cancel') c
    #             LEFT JOIN hr_employee e ON (e.id = c.employee_id)
    #             LEFT JOIN (
    #                 SELECT employee_id, contract_end
    #                 FROM (SELECT employee_id, MAX(COALESCE(date_end, current_date)) as contract_end FROM hr_contract WHERE state != 'cancel' GROUP BY employee_id) c_end
    #                 WHERE c_end.contract_end < current_date) exit on (exit.employee_id = c.employee_id)
    #             LEFT JOIN (
    #                 SELECT employee_id, MIN(date_start) as contract_start
    #                 FROM hr_contract WHERE state != 'cancel'
    #                 GROUP BY employee_id) start on (start.employee_id = c.employee_id)
    #              %s
    #             CROSS JOIN generate_series(c.date_start, (CASE WHEN c.date_end IS NULL THEN current_date + interval '1 year' ELSE (CASE WHEN date_part('day', c.date_end) < date_part('day', c.date_start) THEN c.date_end + interval '1 month' ELSE c.date_end END) END), interval '1 month') serie
    #     """ % from_clause

    #     return '(SELECT * %s FROM (SELECT %s FROM %s) in_query)' % (outer, select_, from_)

    # def init(self):
    #     tools.drop_view_if_exists(self.env.cr, self._table)
    #     self.env.cr.execute("""CREATE or REPLACE VIEW %s as (%s)""" % (self._table, self._query()))    
    
    def name_get(self):
        result = []
        for record in self:
            name = f"[{record.code}] {record.name.name}"
            result.append((record.id, name))
        return result
    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        if not args:
            args = []
        if name:
            session_ids = self._search([('code', operator, name)] + args, limit=limit, access_rights_uid=name_get_uid)
            if not session_ids:
                session_ids = self._search([('name', operator, name)] + args, limit=limit, access_rights_uid=name_get_uid)
        else:
            session_ids = self._search(args, limit=limit, access_rights_uid=name_get_uid)
        return session_ids #models.lazy_name_get(self.browse(course_ids).with_user(name_get_uid))
        
    @api.model
    def create(self, vals):
        if vals.get('code', _('New')) == _('New'):
            plan_date = vals.get('start_date')
            vals['code'] = self.env['ir.sequence'].next_by_code('lms.session', sequence_date=plan_date)
        return super(Session, self).create(vals)    
        
    def action_open_barcode_scanner(self):
        action = self.env.ref('taps_lms.action_barcode_scanner').read()
        _logger.info("Action Data: %s", action)
        action = action[0]
        context = dict(self.env.context, active_id=self.id)
        action['context'] = context
        return action        
    
    @api.model
    def attendance_scan(self, barcode, activeId=None):        
        """ Receive a barcode scanned from the LMS Mode and change the attendances of corresponding employee.
            Returns either an action or a warning.
        """
        employee = self.env['hr.employee'].search([('barcode', '=', barcode)], limit=1)
        # raise UserError((activeId))
        if employee:
            return self._attendance_action('taps_lms.session_list_action', barcode=barcode, activeId=activeId)
        return {'warning': _("No employee corresponding to Badge ID '%(barcode)s.'") % {'barcode': barcode}}

    def attendance_manual(self, next_action, entered_pin=None):
        self.ensure_one()
        employee = self.env['hr.employee']
        attendance_user_and_no_pin = self.user_has_groups(
            'hr_attendance.group_hr_attendance_user,'
            '!hr_attendance.group_hr_attendance_use_pin')
        can_check_without_pin = attendance_user_and_no_pin or (self.user_id == self.env.user and entered_pin is None)
        if can_check_without_pin or entered_pin is not None and entered_pin == employee.pin:
            return self._attendance_action(next_action)
        return {'warning': _('Wrong PIN')}

    def _attendance_action(self, next_action, barcode=None, activeId=None):
        # raise UserError((barcode,activeId))
        """ Changes the attendance of the employee.
            Returns an action to the check in/out message,
            next_action defines which menu the check in/out message should return to. ("My Attendances" or "Kiosk Mode")
        """
        # self.ensure_one()
        
        employee = self.env['hr.employee'].search([('barcode', '=', barcode)], limit=1)
        action_message = self.env["ir.actions.actions"]._for_xml_id("taps_lms.action_greeting_message")
        action_message['active_id'] = activeId
        action_message['previous_attendance_change_date'] = employee.last_attendance_id and (employee.last_attendance_id.check_out or employee.last_attendance_id.check_in) or False
        action_message['employee_id'] = employee.id
        action_message['employee_name'] = employee.name
        action_message['barcode'] = employee.barcode
        action_message['next_action'] = next_action
        action_message['hours_today'] = employee.hours_today
        action_message['att_date'] = fields.Datetime.now()

        if employee.user_id:
            modified_attendance = self.with_user(employee.user_id)._attendance_action_change(barcode, activeId)
        else:
            modified_attendance = self._attendance_action_change(barcode, activeId)
            
        action_message['attendance'] = modified_attendance.read()[0]
        return {'action': action_message}

    def _attendance_action_change(self, barcode=None, activeId=None):
        """ Check In/Check Out action
            Check In: create a new attendance record
            Check Out: modify check_out field of the appropriate attendance record
        """
        employee = self.env['hr.employee'].search([('barcode', '=', barcode)], limit=1)
        action_date = fields.Datetime.now()
    
        # Check if the employee exists with the given barcode
        if not employee:
            raise UserError(_("Employee with barcode '%s' not found.") % barcode)
    
        # Search for the attendance record based on the session_id and attendee_id
        attendance = self.env['lms.session.attendance'].search([
            ('session_id', '=', activeId),
            ('attendee_id', '=', employee.id),
        ], limit=1)
    
        if not attendance:
            # If attendance record doesn't exist, create a new one
            vals = {
                'session_id': activeId,
                'attendee_id': employee.id,
                'attendance_date': action_date,
            }
            return self.env['lms.session.attendance'].create(vals)
        else:
            # If attendance record exists, update the attendance_date (Check Out)
            attendance.attendance_date = action_date
            return attendance        

    def mark_attendance(self):
         return {
            'name': "Mark Attendance",
            'view_mode': 'tree,form',
            'res_model': 'lms.session.attendance',
            'type': 'ir.actions.act_window',
            'domain': [('session_id', '=', self.id)],
            'context': {
                'default_session_id': self.id,
            },
        }        


    def number_of_attendees(self):
        return len(self.attendee_ids)

    def action_send_session_by_email_cron(self):
        session_ids = self.env['lms.session'].search([('email_sent', '=', False)])
        for session in session_ids:
            if session.email_sent is False:
                session.action_send_session_by_email()
                session.email_sent = True

    @profile()
    def action_send_session_by_email(self):
        # for attendee in self.attendee_ids:
        ctx = {}
        email_list = self.attendee_ids.mapped('email')
        if email_list:
            ctx['email_to'] = ','.join([email for email in email_list if email])
            ctx['email_from'] = self.env.user.company_id.email
            ctx['send_email'] = True
            ctx['attendee'] = ''
            template = self.env.ref('taps_lms.email_template_lms_session')
            template.with_context(ctx).send_mail(self.id, force_send=False, raise_exception=False)

    @api.depends('attendee_ids')
    def _get_attendees_count(self):
        for r in self:
            r.attendees_count = len(r.attendee_ids)

    @api.depends('start_date', 'duration')
    def _get_end_date(self):
        for r in self:
            if not (r.start_date and r.duration):
                r.end_date = r.start_date
                continue

            # Add duration to start_date, but: Monday + 5 days = Saturday, so
            # subtract one second to get on Friday instead
            duration = timedelta(hours=r.duration)
            r.end_date = r.start_date + duration

    def _set_end_date(self):
        for r in self:
            if not (r.start_date and r.end_date):
                continue

            # Compute the difference between dates, but: Friday - Monday = 4 days,
            # so add one day to get 5 days instead
            r.duration = (r.end_date - r.start_date).days + 1

    @api.constrains('instructor_id', 'attendee_ids')
    def _check_instructor_not_in_attendees(self):
        for r in self:
            if r.instructor_id and r.instructor_id in r.attendee_ids:
                raise ValidationError("A session's instructor can't be an attendee")

    @api.depends('seats', 'attendee_ids')
    def _taken_seats(self):
        for r in self:
            if not r.seats:
                r.taken_seats = 0.0
            else:
                r.taken_seats = 100.0 * len(r.attendee_ids) / r.seats

    @api.onchange('seats', 'attendee_ids')
    def _verify_valid_seats(self):
        if self.seats < 0:
            return {
                'warning': {
                    'title': "Incorrect 'seats' value",
                    'message': "The number of available seats may not be negative",
                },
            }
        if self.seats < len(self.attendee_ids):
            return {
                'warning': {
                    'title': "Too many attendees",
                    'message': "Increase seats or remove excess attendees",
                },
            }

class SessionAttendance(models.Model):
    _name = 'lms.session.attendance'
    _description = "Training Session Attendance"
    _rec_name = 'attendee_id'      

    attendee_id = fields.Many2one('hr.employee', string="Employee", required=True)
    company_id = fields.Many2one(related='attendee_id.company_id', store=True)
    department_id = fields.Many2one(related='attendee_id.department_id', store=True)
    attendance_date = fields.Datetime(string="Attendance Date", default=fields.datetime.today(), required=True)
    is_present = fields.Boolean(string="Is Present", default=True)
    session_id = fields.Many2one('lms.session', string="Session", required=True, ondelete='cascade')
    criteria_id = fields.Many2one(related='session_id.course_id.criteria_id', store=True)
    title_id = fields.Many2one(related='session_id.course_id.title_ids', store=True)
    description_id = fields.Text(related='session_id.course_id.description', store=True)
    instructor_id = fields.Many2one(related='session_id.instructor_id', store=True)    
    session_name = fields.Many2one(related='session_id.name', store=True)
    start_date = fields.Datetime(related='session_id.start_date', string="Training Date", store=True)
    duration = fields.Float(related='session_id.duration', store=True)   
            

