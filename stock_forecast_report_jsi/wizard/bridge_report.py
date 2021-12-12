import base64
import io
import logging
from psycopg2 import Error, OperationalError
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import xlsxwriter
from odoo.tools.float_utils import float_round as round
from odoo.tools import format_date
from datetime import date, datetime, time, timedelta
from odoo import fields, models
from dateutil.relativedelta import relativedelta
import math
_logger = logging.getLogger(__name__)


class StockBridgeReport(models.TransientModel):
    _name = 'stock.bridge.report'
    _description = 'Bridge Report'

    report_by = fields.Selection([
        ('by_categories', 'By Categories'),
        ('by_items', 'By Items')],
        default='by_categories')
    categ_ids = fields.Many2many('category.type', string='Categories')
    product_ids = fields.Many2many('product.product')
    stock_date = fields.Date('Stock Date', default=fields.Date.context_today)
    file_data = fields.Binary(readonly=True, attachment=False)
    
    
    def getopening_qty(self,productid,fr_date):
        stock_details = self.env['stock.valuation.layer'].search([('product_id', '=', productid),('schedule_date', '<', fr_date)])
        qty = sum(stock_details.mapped('quantity'))
        return qty
    
    def getopening_val(self,productid,from_date):
        stock_details = self.env['stock.valuation.layer'].search([('product_id', '=', productid),('schedule_date', '<', from_date),('description','not like','%LC/%')])
        val = sum(stock_details.mapped('value'))
        
        landedcost = self.env['stock.landed.cost'].search([('state', '=', 'done'),('date', '<', from_date.date())])
        
        lclist = landedcost.mapped('id')
        lc_details = self.env['stock.valuation.adjustment.lines'].search([('product_id', '=', productid),('cost_id', 'in', (lclist))])
        lc_val = 0
        if len(lc_details)>0:
            lc_val = sum(lc_details.mapped('additional_landed_cost'))
            val = val + lc_val
        return val
    
    def getreceive_qty(self,productid,from_date,stock_date):
        stock_details = self.env['stock.valuation.layer'].search([('product_id', '=', productid),('quantity', '>=', 0),('schedule_date', '>=', from_date),('schedule_date', '<=', stock_date),('description','not like','%Product Quantity Updated%')])
        qty = sum(stock_details.mapped('quantity'))
        return qty
    
    def getreceive_val(self,productid,from_date,stock_date):
        stock_details = self.env['stock.valuation.layer'].search([('product_id', '=', productid),('value', '>=', 0),('schedule_date', '>=', from_date),('schedule_date', '<=', stock_date),('description','not like','%Product Quantity Updated%'),('description','not like','%LC/%')])
        val = sum(stock_details.mapped('value'))
        
        landedcost = self.env['stock.landed.cost'].search([('state', '=', 'done'),('date', '>=', from_date.date()),('date', '<=', stock_date.date())])
        
        lclist = landedcost.mapped('id')
        lc_details = self.env['stock.valuation.adjustment.lines'].search([('product_id', '=', productid),('cost_id', 'in', (lclist))])
        lc_val = 0
        if len(lc_details)>0:
            lc_val = sum(lc_details.mapped('additional_landed_cost'))
            val = val + lc_val
        return val
    
    def getissue_qty(self,productid,from_date,stock_date):
        stock_details = self.env['stock.valuation.layer'].search([('product_id', '=', productid),('quantity', '<', 0),('schedule_date', '>=', from_date),('schedule_date', '<=', stock_date),('description','not like','%Product Quantity Updated%')])
        qty = sum(stock_details.mapped('quantity'))
        return qty
    
    def getissue_val(self,productid,from_date,stock_date):
        stock_details = self.env['stock.valuation.layer'].search([('product_id', '=', productid),('value', '<', 0),('schedule_date', '>=', from_date),('schedule_date', '<=', stock_date),('description','not like','%Product Quantity Updated%')])
        val = sum(stock_details.mapped('value'))
        return val

    def getclosing_qty(self,productid,stock_date):
        stock_details = self.env['stock.valuation.layer'].search([('product_id', '=', productid),('schedule_date', '<', stock_date)])
        qty = sum(stock_details.mapped('quantity'))
        return qty
    
    def getclosing_val(self,productid,stock_date):
        stock_details = self.env['stock.valuation.layer'].search([('product_id', '=', productid),('schedule_date', '<', stock_date),('description','not like','%LC/%')])
        val = sum(stock_details.mapped('value'))
        
        landedcost = self.env['stock.landed.cost'].search([('state', '=', 'done'),('date', '<', stock_date.date())])
        
        lclist = landedcost.mapped('id')
        lc_details = self.env['stock.valuation.adjustment.lines'].search([('product_id', '=', productid),('cost_id', 'in', (lclist))])
        lc_val = 0
        if len(lc_details)>0:
            lc_val = sum(lc_details.mapped('additional_landed_cost'))
            val = val + lc_val
        return val
    def float_to_time(self,hours):
        if hours == 24.0:
            return time.max
        fractional, integral = math.modf(hours)
        return time(int(integral), int(round(60 * fractional, precision_digits=0)), 0)    
    
    def print_bridge_report(self):
        Move = self.env['stock.valuation.layer']
        Product = self.env['product.product'].search([('default_code', 'like', 'R_')])
        start_time = fields.datetime.now()
        t_date = self.stock_date
        hour_from = 0.0
        hour_to = 23.98
        combine = datetime.combine
        stock_date = combine(t_date, self.float_to_time(hour_to))
        
        last_m_s_day = combine(t_date.replace(day=1), self.float_to_time(hour_from))
        last_m_e_day = stock_date
        
        sec_e_day = t_date.replace(day=1) - timedelta(days=1)
        sec_s_day = t_date.replace(day=1) - timedelta(days=sec_e_day.day)
        
        sec_m_s_day = combine(sec_s_day, self.float_to_time(hour_from))
        sec_m_e_day = combine(sec_e_day, self.float_to_time(hour_to))
        
        fst_day = t_date - relativedelta(months = 1)
        fst_e_day = fst_day.replace(day=1) - timedelta(days=1)
        fst_s_day = fst_day.replace(day=1) - timedelta(days=fst_e_day.day)
        
        fst_m_s_day = combine(fst_s_day, self.float_to_time(hour_from))
        fst_m_e_day = combine(fst_e_day, self.float_to_time(hour_to))
        
        m1 = fst_m_s_day.strftime("%B,%y")
        m2 = sec_m_s_day.strftime("%B,%y")
        m3 = last_m_s_day.strftime("%B,%y")
        #raise UserError((fst_m_s_day,fst_m_e_day,sec_m_s_day,sec_m_e_day,last_m_s_day,last_m_e_day))
        
        #raise UserError((from_date,stock_date))
        if not (self.product_ids or self.categ_ids):
            products = Product.search([('type', '=', 'product'),('default_code', 'like', 'R_')])
        elif self.report_by == 'by_items':
            products = self.product_ids
        else:
            products = Product.search([('categ_type', 'in', self.categ_ids.ids),('default_code', 'like', 'R_')])
        # Date wise opening quantity
        #product_quantities = products._compute_quantities_dict(False, False, False, from_date, stock_date)
        report_data = []

        for categ in products.categ_type:
            #report_data.append([categ.display_name])
            categ_products = products.filtered(lambda x: x.categ_type == categ)
            #stock_details = self.env['category.type'].search([('product_id', '=', productid),('schedule_date', '<', stock_date)])
            report_product_data = []
            product_cat_data = []
            for product in categ_products:
                product_data = []
                received_qty = received_price_unit = issued_qty = issued_value = 0
                product_id = product.id
                
                fst_issued_qty=0
                sec_issued_qty=0
                lst_issued_qty=0
                
                fst_issued_value=0
                sec_issued_value=0
                lst_issued_value=0
                closing_qty=0
                closing_value=0
                avg_qty=0
                avg_value=0
                fst_issued_qty = self.getissue_qty(product_id,fst_m_s_day,fst_m_e_day)
                fst_issued_value = self.getissue_val(product_id,fst_m_s_day,fst_m_e_day)
                
                sec_issued_qty = self.getissue_qty(product_id,sec_m_s_day,sec_m_e_day)
                sec_issued_value = self.getissue_val(product_id,sec_m_s_day,sec_m_e_day)
                
                lst_issued_qty = self.getissue_qty(product_id,last_m_s_day,last_m_e_day)
                lst_issued_value = self.getissue_val(product_id,last_m_s_day,last_m_e_day)
                
                fst_issued_qty = abs(fst_issued_qty)
                sec_issued_qty = abs(sec_issued_qty)
                lst_issued_qty = abs(lst_issued_qty)
                
                avg_qty = round((fst_issued_qty+sec_issued_qty+lst_issued_qty)/3,0)
                avg_value = round((fst_issued_value+sec_issued_value+lst_issued_value)/3,0)
                # Prepare Closing Quantity
                closing_qty = self.getclosing_qty(product_id,stock_date)
                closing_value = self.getclosing_val(product_id,stock_date)
                
                closing_qty = abs(closing_qty)
                closing_value = abs(closing_value)
                
                value_a = avg_value
                if value_a <= 0:
                    value_a = 1
                
                num_day = round((closing_value/value_a)*30,0)
                #num_day = round((closing_value/avg_value)*30)
                #raise UserError((num_day))
                #fst_m_s_day,fst_m_e_day,sec_m_s_day,sec_m_e_day,last_m_s_day,last_m_e_day
                product_data = [
                    '',
                    '',
                    product.name,
                    closing_qty,
                    closing_value,
                    fst_issued_qty,
                    fst_issued_value,
                    sec_issued_qty,
                    sec_issued_value,
                    lst_issued_qty,
                    lst_issued_value,
                    avg_qty,
                    avg_value,
                    num_day,
                ]
                report_product_data.append(product_data)
            
            closing_categ_qty=sum(row[3] for row in report_product_data)
            closing_categ_value=sum(row[4] for row in report_product_data)
            fst_categ_qty=sum(row[5] for row in report_product_data)
            fst_categ_value=sum(row[6] for row in report_product_data)
            sec_categ_qty=sum(row[7] for row in report_product_data)
            sec_categ_value=sum(row[8] for row in report_product_data)
            lst_categ_qty=sum(row[9] for row in report_product_data)
            lst_categ_value=sum(row[10] for row in report_product_data)
            avg_categ_qty=sum(row[11] for row in report_product_data)
            avg_categ_value=sum(row[12] for row in report_product_data)
            
            num_day_categ =sum(row[13] for row in report_product_data)
            
            parent_type = ''
            if categ.parent_id.name:
                parent_type = categ.parent_id.name
            product_cat_data = [
                    parent_type,
                    categ.name,
                    '',
                    closing_categ_qty,
                    closing_categ_value,
                    fst_categ_qty,
                    fst_categ_value,
                    sec_categ_qty,
                    sec_categ_value,
                    lst_categ_qty,
                    lst_categ_value,
                    avg_categ_qty,
                    avg_categ_value,
                    num_day_categ,
                ]
            
            report_data.append(product_cat_data)
            if self.report_by == 'by_items':
                for prodata in report_product_data:
                    report_data.append(prodata)

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet()

        report_title_style = workbook.add_format({'align': 'center', 'bold': True, 'font_size': 16, 'bg_color': '#C8EAAB'})
        worksheet.merge_range('C2:F2', 'Bridge Report', report_title_style)

        report_small_title_style = workbook.add_format({'bold': True, 'font_size': 14})
        
        #('%s-%s-%s' % (format_date(self.env, from_date), format_date(self.env, to_date)))
        #m1 = fst_m_s_day.strftime("%B,%y")
        #m2 = sec_m_s_day.strftime("%B,%y")
        #m3 = last_m_s_day.strftime("%B,%y")
        
        #worksheet.write(3, 3, (m1, m2, m3), report_small_title_style)
        worksheet.merge_range('D6:E6', 'Closing Stock', report_title_style)
        worksheet.merge_range('F6:G6', m1, report_title_style)
        worksheet.merge_range('H6:I6', m2, report_title_style)
        worksheet.merge_range('J6:K6', m3, report_title_style)
        worksheet.merge_range('L6:M6', 'Avg Consumption', report_title_style)
        
        column_product_style = workbook.add_format({'bold': True, 'bg_color': '#EEED8A', 'font_size': 12})
        column_received_style = workbook.add_format({'bold': True, 'bg_color': '#A2D374', 'font_size': 12})
        column_issued_style = workbook.add_format({'bold': True, 'bg_color': '#F8715F', 'font_size': 12})
        row_categ_style = workbook.add_format({'bold': True, 'bg_color': '#6B8DE3'})

        # set the width od the column
        
        worksheet.set_column(0, 13, 20)
        
        worksheet.write(6, 0, 'Product', column_product_style)        
        worksheet.write(6, 1, 'Category', column_product_style)
        worksheet.write(6, 2, 'Item', column_product_style)
        worksheet.write(6, 3, 'Quantity', column_product_style)
        worksheet.write(6, 4, 'Value', column_product_style)
        worksheet.write(6, 5, 'Quantity', column_received_style)
        worksheet.write(6, 6, 'Value', column_received_style)
        worksheet.write(6, 7, 'Quantity', column_received_style)
        worksheet.write(6, 8, 'Value', column_received_style)
        worksheet.write(6, 9, 'Quantity', column_received_style)
        worksheet.write(6, 10, 'Value', column_received_style)
        worksheet.write(6, 11, 'Quantity', column_issued_style)
        worksheet.write(6, 12, 'Value', column_issued_style)
        worksheet.write(6, 13, 'Number of Day', column_issued_style)
        col = 0
        row=7
        
        for line in report_data:
            col=0
            categ=False
            for l in line:
                if l != '' and col==1 :
                    categ=True
                if categ==True:
                    worksheet.write(row, col, l, row_categ_style)
                else:
                    worksheet.write(row, col, l)
                col+=1
            row+=1
        workbook.close()
        xlsx_data = output.getvalue()

        self.file_data = base64.encodebytes(xlsx_data)
        end_time = fields.datetime.now()
        _logger.info("\n\nTOTAL PRINTING TIME IS : %s \n" % (end_time - start_time))
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/?model={}&id={}&field=file_data&filename={}&download=true'.format(self._name, self.id, 'BridgeReport'),
            'target': 'self',
        }