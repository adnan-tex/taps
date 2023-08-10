from odoo import models, fields, api


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    instructor = fields.Boolean("Instructor", default=False)
    session_ids = fields.Many2many('lms.session', string="Attended Sessions", compute='_compute_session_ids', store=True)

    def _compute_session_ids(self):
        for employee in self:
            employee.session_ids = self.env['lms.session'].search([('attendance_ids.attendee_id', '=', employee.id)])

class HrEmployeePublic(models.Model):
    # _name = "hr.employee.public"
    _inherit = ["hr.employee.public"]
    _description = 'Public Employee'

    # Fields coming from hr.employee.base
    instructor = fields.Boolean(readonly=True)
    session_ids = fields.Many2many(readonly=True)