# -*- coding: utf-8 -*-
{
    'name': "Taps HR",
    'summary': """Customization for HR Employee, HR Attendance""",

    'description': """This module integrates Odoo with the hr, employee, attendance""",

    'author': "Mohammad Adnan",
    'website': "http://www.odoo.com",
    'category': 'Generic Modules/Human Resources',
    "version": "14.0.1.0.0",
    "license": "OEEL-1",
    'depends': ['base_setup', 'hr_attendance', 'web_studio','hr','hr_payroll_account','hr_payroll'],
    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/employee_id_generate.xml',
        'data/attendance_date_generate.xml',
        'data/attendance_flag_generate.xml',
        'data/overtime_calculate.xml',
        'views/attendance_views.xml',
        'views/employee_views.xml',
        'views/contract_views.xml',
        'views/hr_work_entry_views.xml',
        'views/hr_payslip_views.xml',
        'views/hr_payslip_input_views.xml',
        'views/salary_adjustment_views.xml',
        'reports/salary_sheet.xml',
        'reports/top_sheet_summary.xml',
        'reports/report.xml',
        'reports/custom_header_footer.xml',
        'reports/header_footer.xml',
        'reports/salary_headwise_pdf_report.xml',
        'reports/jobcard_pdf_report.xml',
        'reports/paperformat.xml',
        'wizard/report_wizard_view.xml',
    ],
    # only loaded in demonstration mode
    'demo': [],
    'installable': True,
    'auto_install': True,
    'application': True,
    'images': ['static/description/icon.png'],
}
