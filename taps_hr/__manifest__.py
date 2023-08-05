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
    'depends': ['base_setup', 'hr_attendance', 'web_studio','hr','hr_payroll_account','hr_payroll','barcodes','hr_appraisal'],
    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/activity.xml',
        'data/employee_id_generate.xml',
        'data/attendance_date_generate.xml',
        'data/attendance_flag_generate.xml',
        'data/overtime_calculate.xml',
        'data/salary_adjustment_code_generate.xml',
        'data/increment_code_generate.xml',
        'data/employee_service_length_generate.xml',
        'data/create_contact.xml',
        'data/create_att_atjoin.xml',
        'data/create_leave_allocation.xml',
        'data/daily_attendance_email.xml',
        'data/marriage_anniversery_wish.xml',
        'data/birthday_wish_email.xml',
        'data/work_anniversery_wish.xml',
        'views/web_asset_backend_template.xml',        
        'views/attendance_views.xml',
        'views/employee_views.xml',
        'views/contract_views.xml',
        'views/hr_work_entry_views.xml',
        'views/hr_payslip_views.xml',
        'views/hr_payslip_input_views.xml',
        'views/salary_adjustment_views.xml',
        'views/increment_promotion_views.xml',
#         'views/bulk_attendance_views.xml',
        'views/hr_appraisal_goal_views.xml',
        'views/hr_appraisal_goal_acvd_views.xml',
        'views/track_template.xml',
        
        'reports/paperformat.xml',        
        'reports/report_action_menu.xml',
        'reports/custom_header_footer.xml',
        'reports/header_footer.xml',
        
        'reports/pay_slip.xml',
        'reports/fnf_slip.xml',
        'reports/salary_sheet.xml',
        'reports/top_sheet_summary.xml',
        'reports/bonus_sheet.xml',
        'reports/bonus_top_sheet_summary.xml',
        'reports/salary_headwise_pdf_report.xml',
        'reports/increment_letter.xml',
#         'reports/kiosk_job_pdf_template.xml',
#         'reports/employee_card_pdf_report.xml',
        'reports/hris_employee_profile_pdf_report.xml',
        'reports/hris_appointment_letter_pdf_report.xml',
        'reports/hris_attendance_calendar_pdf_report.xml',
        'reports/hris_birth_calendar_pdf_report.xml',
        'reports/hris_anniversary_calendar_pdf_report.xml',
        'reports/hris_confirmation_letter_pdf_report.xml',
        'reports/hris_joining_letter_pdf_report.xml',
        'reports/hris_loan_application_pdf_report.xml',
        'reports/hris_pf_loan_application_pdf_report.xml',
        'reports/hris_acopening_pdf_template.xml',
        'reports/hris_marriage_gift_pdf_report.xml',
        'reports/hris_no_dues_letter_pdf_report.xml',
        'reports/hris_pf_statement_pdf_report.xml',
        'reports/hris_retention_risk_matrix_report.xml',
        'reports/hris_retentionincentive_letter_pdf_report.xml',
        #'reports/hris_shift_pdf_report.xml',
        'reports/hris_trail_extension_letter_pdf_report.xml',
        'reports/hris_training_pdf_report.xml',
        'reports/atten_job_pdf_template.xml',
        'reports/atten_dailyatten_pdf_template.xml',
        'reports/atten_dailyattenot_pdf_template.xml',
        'reports/atten_dailyattenots_pdf_template.xml',
        'reports/atten_dailymanpower_pdf_template.xml',
        'reports/atten_head_count_pdf_template.xml',
        'reports/atten_payroll_planning_pdf_template.xml',
        'reports/atten_monthly_manhours_pdf_template.xml',
        'reports/atten_daily_manhours_pdf_template.xml',
        'reports/atten_daily_ot_analysis_pdf_template.xml',
        'reports/atten_daily_atten_summary_pdf_template.xml',
        'reports/atten_monthly_atten_summary_pdf_template.xml',
        'reports/atten_holiday_slip_pdf_template.xml',
        'reports/atten_daily_excess_ot_pdf_template.xml',
        'reports/atten_daily_salary_cost_pdf_template.xml',
        'reports/atten_atten_calender_pdf_template.xml',
        'reports/atten_shift_schedule_pdf_template.xml',
        'reports/kpi_objective_pdf_template.xml',
        'reports/kpi_objective_score_pdf_template.xml',
        'reports/kpi_objective_score_quarter_pdf_template.xml',
#         'wizard/employee_profile_report_wizard_view.xml',
        'wizard/headwise_report_wizard_view.xml',
#         'wizard/jobcard_report_wizard_view.xml',
        'wizard/salary_report_wizard_view.xml',
        'wizard/att_reprocess_wizard_view.xml',
#         'wizard/kiosk_jobcard.xml',
        'wizard/hris_report_wizard_view.xml',
        'wizard/attendance_report_wizard_view.xml',
        'wizard/appraisal_report_wizard_view.xml',
    ],
    'demo': [],
    'qweb': [
        "static/src/xml/attendance.xml",
    ],    
    'installable': True,
    'auto_install': False,
    'application': True,
    'images': ['static/description/icon.png'],
}
