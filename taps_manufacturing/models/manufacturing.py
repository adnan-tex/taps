import json
import datetime
import math
import operator as py_operator
import re

from collections import defaultdict
from dateutil.relativedelta import relativedelta
from itertools import groupby

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools import float_compare, float_round, float_is_zero, format_datetime
from odoo.tools.misc import format_date

from odoo.addons.stock.models.stock_move import PROCUREMENT_PRIORITIES

from werkzeug.urls import url_encode
from datetime import datetime

SIZE_BACK_ORDER_NUMERING = 3


class ManufacturingOrder(models.Model):
    _name = "manufacturing.order"
    #_inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = "Manufacturing Order"
    #_order = 'date_order desc, id desc'
    _check_company_auto = True

    #sequence = fields.Integer(string='Sequence')
    sale_order_line = fields.Many2one('sale.order.line', string='Sale Order Line', readonly=True, store=True)
    oa_id = fields.Many2one('sale.order', related='sale_order_line.order_id', string='OA', readonly=True, store=True, domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", check_company=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True, store=True, required=True, index=True, default=lambda self: self.env.company.id)
    partner_id = fields.Many2one('res.partner', related='oa_id.partner_id', string='Customer', readonly=True)
    #buyer_name = fields.Many2one('sale.buyer', related='oa_id.buyer_name.id', string='Buyer', readonly=True)
    buyer_name = fields.Char(string='Buyer', readonly=True)
    payment_term = fields.Many2one('account.payment.term', related='oa_id.payment_term_id', string='Payment Term', readonly=True)
    date_order = fields.Datetime(string='Order Date', related='oa_id.date_order', readonly=True)
    validity_date = fields.Date(string='Expiration', related='oa_id.validity_date', readonly=True)
    
    lead_time = fields.Integer(string='Lead Time', compute='get_leadtime', readonly=True)
    
    product_id = fields.Many2one(
        'product.product', related='sale_order_line.product_id', string='Product Id',ondelete='restrict', check_company=True)  # Unrequired company
    product_template_id = fields.Many2one(
        'product.template', string='Product',
        related="product_id.product_tmpl_id", domain=[('sale_ok', '=', True)])
    fg_categ_type = fields.Selection(related='product_template_id.fg_categ_type', string='Item')
    product_uom = fields.Many2one('uom.uom', string='Unit', related='product_template_id.uom_id')
    product_uom_qty = fields.Float(string='Quantity', related='sale_order_line.product_uom_qty', digits='Product Unit of Measure', readonly=True)
    done_qty = fields.Float(string='Done Qty', digits='Product Unit of Measure', readonly=False)
    balance_qty = fields.Float(string='Balance', compute='_balance_qty', digits='Product Unit of Measure', readonly=True)
    
    topbottom = fields.Char(string='Top/Bottom', store=True, readonly=True)
    slidercodesfg = fields.Char(string='Slider', store=True, readonly=True)
    finish = fields.Char(string='Finish', store=True, readonly=True)
    shade = fields.Char(string='Shade', store=True, readonly=True)
    sizein = fields.Char(string='Size (Inch)', store=True, readonly=True)
    sizecm = fields.Char(string='Size (CM)', store=True, readonly=True)
    sizemm = fields.Char(string='Size (MM)', store=True, readonly=True)
    
    dyedtape = fields.Char(string='Dyed Tape', store=True, readonly=True)
    ptopfinish = fields.Char(string='Top Finish', store=True, readonly=True)
    
    numberoftop = fields.Char(string='N.Top', store=True, readonly=True)
    
    pbotomfinish = fields.Char(string='Bottom Finish', store=True)
    ppinboxfinish = fields.Char(string='Pin-Box Finish', store=True)
    dippingfinish = fields.Char(string='Dipping Finish', store=True)
    gap = fields.Char(string='Gap', store=True)
    
    logo = fields.Text(string='Logo', store=True)
    logoref = fields.Text(string='Logo Ref', store=True)
    logo_type = fields.Text(string='Logo Type', store=True)
    style = fields.Text(string='Style', store=True)
    gmt = fields.Text(string='Gmt', store=True)
    shapefin = fields.Text(string='Shape Finish', store=True)
    bcdpart = fields.Text(string='BCD Part Material Type / Size', store=True)
    b_part = fields.Text(string='B Part', store=True)
    c_part = fields.Text(string='C Part', store=True)
    d_part = fields.Text(string='D Part', store=True)
    finish_ref = fields.Text(string='Finish Ref', store=True)
    product_code = fields.Text(string='Product Code', store=True)
    shape = fields.Text(string='Shape', store=True)
    nailmat = fields.Text(string='Nail Material / Type / Shape / Size', store=True)
    nailcap = fields.Text(string='Nail Cap Logo', store=True)
    fnamebcd = fields.Text(string='Finish Name ( BCD/NAIL/ NAIL CAP)', store=True)
    nu1washer = fields.Text(string='1 NO. Washer Material & Size', store=True)
    nu2washer = fields.Text(string='2 NO. Washer Material & Size', store=True)
    back_part = fields.Text(string='Back Part', store=True)
    
    tape_con = fields.Float('Tape C.', compute='_get_line_value', readonly=True, digits='Unit Price')
    slider_con = fields.Float('Slider C.', compute='_get_line_value', readonly=True, digits='Unit Price')
    topwire_con = fields.Float('Topwire C.', compute='_get_line_value', readonly=True, digits='Unit Price')
    botomwire_con = fields.Float('Botomwire C.', compute='_get_line_value', readonly=True, digits='Unit Price')
    tbwire_con = fields.Float('TBwire C.', compute='_get_line_value', readonly=True, digits='Unit Price')
    wire_con = fields.Float('Wire C.', compute='_get_line_value', readonly=True, digits='Unit Price')
    pinbox_con = fields.Float('Pinbox C.', compute='_get_line_value', readonly=True, digits='Unit Price')
    shadewise_tape = fields.Float('Shadwise Tape', compute='_get_line_value', readonly=True, digits='Unit Price')

    dyeing_plan = fields.Datetime(string='Dye Plan', readonly=False)
    dyeing_plan_end = fields.Datetime(string='Dye Plan End', readonly=False)
    dyeing_plan_qty = fields.Float(string='Dye Plan Qty', readonly=False)
    dy_rec_plan_qty = fields.Float(string='Dye Last Plan', readonly=False, default=0.0)
    dyeing_plan_due = fields.Float(string='Dye Plan Due', readonly=False, default=0.0, compute='_dy_plane_due')
    dyeing_output = fields.Float(string='Dye Output', readonly=False, default=0.0)
    dyeing_qc_pass = fields.Float(string='Dye QC Pass', readonly=False, default=0.0)

    plating_plan = fields.Datetime(string='Plat/Paint Start', readonly=False)
    plating_plan_end = fields.Datetime(string='Plat/Paint End', readonly=False)
    plating_plan_qty = fields.Float(string='Plat/Paint Plan Qty', readonly=False)
    pl_rec_plan_qty = fields.Float(string='Plat/Paint Rceplan Qty', readonly=False, default=0.0)
    plating_output = fields.Float(string='Plat/Paint Output', readonly=False)
    #plating_qc_pass = fields.Float(string='Plating QC Pass', readonly=False)

    top_plat_plan = fields.Datetime(string='Top Plat/Paint Start', readonly=False)
    top_plat_plan_end = fields.Datetime(string='Top Plat/Paint End', readonly=False)
    top_plat_plan_qty = fields.Float(string='Top Plat/Paint Plan Qty', readonly=False)
    tpl_rec_plan_qty = fields.Float(string='Top Plat/Paint Recplan Qty', readonly=False, default=0.0)
    top_plat_output = fields.Float(string='Top Plat/Paint Output', readonly=False)
    #top_plat_qc_pass = fields.Float(string='Plating QC Pass', readonly=False)

    bot_plat_plan = fields.Datetime(string='Btm Plat/Paint Start', readonly=False)
    bot_plat_plan_end = fields.Datetime(string='Btm Plat/Paint End', readonly=False)
    bot_plat_plan_qty = fields.Float(string='Btm Plat/Paint Plan Qty', readonly=False)
    bpl_rec_plan_qty = fields.Float(string='Btm Plat/Paint Recplan Qty', readonly=False, default=0.0)
    bot_plat_output = fields.Float(string='Btm Plat/Paint Output', readonly=False)
    #bot_plat_qc_pass = fields.Float(string='Plating QC Pass', readonly=False)    

    pin_plat_plan = fields.Datetime(string='Pbox Plat/Paint Start', readonly=False)
    pin_plat_plan_end = fields.Datetime(string='Pbox Plat/Paint End', readonly=False)
    pin_plat_plan_qty = fields.Float(string='Pbox Plat/Paint Plan Qty', readonly=False)
    ppl_rec_plan_qty = fields.Float(string='Pbox Plat/Paint Recplan Qty', readonly=False, default=0.0)
    pin_plat_output = fields.Float(string='Pbox Plat/Paint Output', readonly=False)
    #pin_plat_qc_pass = fields.Float(string='Plating QC Pass', readonly=False)    

    sli_asmbl_plan = fields.Datetime(string='Slider Asmbl Plan Start', readonly=False)
    sli_asmbl_plan_end = fields.Datetime(string='Slider Asmbl Plan End', readonly=False)
    sli_asmbl_plan_qty = fields.Float(string='Slider Asmbl Plan Qty', readonly=False)
    sass_rec_plan_qty = fields.Float(string='Slider Asmbl Rceplan Qty', readonly=False, default=0.0)
    sli_asmbl_output = fields.Float(string='Slider Asmbl Output', readonly=False)

    # painting_done = fields.Float(string='Painting Output', readonly=False)
    # p_plan = fields.Datetime(string='Slider Asmbl Plan Start', readonly=False)
    # sli_asmbl_plan_end = fields.Datetime(string='Slider Asmbl Plan End', readonly=False)
    # sli_asmbl_plan_qty = fields.Float(string='Slider Asmbl Plan Qty', readonly=False)
    # sass_rec_plan_qty = fields.Float(string='Plating Replan Qty', readonly=False, default=0.0)
    # sli_asmbl_output = fields.Float(string='Plating Output', readonly=False)
    
    chain_making_done = fields.Float(string='CM Output', readonly=False)
    diping_done = fields.Float(string='Dipping Output', readonly=False)
    assembly_done = fields.Float(string='Assembly Output', readonly=False)
    packing_done = fields.Float(string='Packing Output', readonly=False)
    
    oa_total_qty = fields.Float(string='OA Total Qty', readonly=True)
    oa_total_balance = fields.Float(string='OA Balance', readonly=True, store=True)#, compute='_oa_balance'
    remarks = fields.Text(string='Remarks')
    num_of_lots = fields.Integer(string='N. of Lots', readonly=True, compute='get_lots')
    
    
    
    @api.onchange('packing_done')
    def _packing_output(self):
        for out in self:
            done_qty = out.done_qty + out.packing_done
            out.done_qty = done_qty
            manufac_ids = self.env["manufacturing.order"].search([('oa_id','=',out.oa_id.id)])
            oa_bal = out.oa_total_balance - out.packing_done
            manu = manufac_ids.update({'oa_total_balance':oa_bal})
            
    def button_createlot(self):
        self.ensure_one()
        self._check_company()
        action = self.env["ir.actions.actions"]._for_xml_id("taps_manufacturing.action_mrp_lot")
        return action
    
    def action_view_lots(self):
        """ This function returns an action that display existing picking orders of given purchase order ids. When only one found, show the picking immediately.
        """
        result = self.env["ir.actions.actions"]._for_xml_id('taps_manufacturing.action_operation_details')
        # override the context to get rid of the default filtering on operation type
        result['context'] = {'mrp_line': self.id, 'operation_of': 'lot'}
        lots_ = self.env['operation.details'].search([('mrp_line', '=', self.id),('operation_of', '=', 'lot')])
        lot_ids = lots_.mapped('id')
        #raise UserError((lot_ids))
        # choose the view_mode accordingly
        result['domain'] = "[('id','in',%s)]" % (lot_ids)
        return result
        
    def get_lots(self):
        for s in self:
            count_lots = self.env['operation.details'].search_count([('mrp_line', '=', s.id),('operation_of', '=', 'lot')])
            s.num_of_lots = count_lots
            #s.lot_ids = count_lots.mapped('id')    

    def _oa_balance(self):
        for s in self:
            mr = self.env["manufacturing.order"].search([('oa_id','=',s.oa_id.id)])
            s.oa_total_balance = s.oa_total_qty-sum(mr.mapped('done_qty'))

    def get_leadtime(self):
        for s in self:
            s.lead_time = (datetime.now() - s.date_order).days
    
    def _balance_qty(self):
        for s in self:
            s.balance_qty = s.product_uom_qty - s.done_qty
    
    def _dy_plane_due(self):
        for s in self:
            s.dyeing_plan_due = s.tape_con - s.dyeing_plan_qty
    
    def _get_line_value(self):
        for s in self:
            s.tape_con = s.sale_order_line.tape_con
            s.slider_con = s.sale_order_line.slider_con
            s.topwire_con = s.sale_order_line.topwire_con
            s.botomwire_con = s.sale_order_line.botomwire_con
            s.tbwire_con = s.sale_order_line.tbwire_con
            s.wire_con = s.sale_order_line.wire_con
            s.pinbox_con = s.sale_order_line.pinbox_con
            s.shadewise_tape = s.sale_order_line.shadewise_tape
            
    #         s.sizecm = s.sale_order_line.sizecm
    #         s.sizemm = s.sale_order_line.sizemm
    #         s.dyedtape = s.sale_order_line.dyedtape
    #         s.ptopfinish = s.sale_order_line.ptopfinish
    #         s.numberoftop = s.sale_order_line.numberoftop
    #         s.pbotomfinish = s.sale_order_line.pbotomfinish
    #         s.ppinboxfinish = s.sale_order_line.ppinboxfinish
    #         s.dippingfinish = s.sale_order_line.dippingfinish
    #         s.gap = s.sale_order_line.gap
    #         s.logo = s.sale_order_line.logo
    #         s.logoref = s.sale_order_line.logoref
    #         s.logo_type = s.sale_order_line.logo_type
    #         s.style = s.sale_order_line.style
    #         s.gmt = s.sale_order_line.gmt
    #         s.shapefin = s.sale_order_line.shapefin
    #         s.bcdpart = s.sale_order_line.bcdpart
    #         s.b_part = s.sale_order_line.b_part
    #         s.c_part = s.sale_order_line.c_part
    #         s.d_part = s.sale_order_line.d_part
    #         s.finish_ref = s.sale_order_line.finish_ref
    #         s.product_code = s.sale_order_line.product_code
    #         s.shape = s.sale_order_line.shape
    #         s.nailmat = s.sale_order_line.nailmat
    #         s.nailcap = s.sale_order_line.nailcap
    #         s.fnamebcd = s.sale_order_line.fnamebcd
    #         s.nu1washer = s.sale_order_line.nu1washer
    #         s.nu2washer = s.sale_order_line.nu2washer
    #         s.back_part = s.sale_order_line.back_part
        

    def button_plan(self):
        self._check_company()
        # if self.state in ("done", "to_close", "cancel"):
        #     raise UserError(
        #         _(
        #             "Cannot split a manufacturing order that is in '%s' state.",
        #             self._fields["state"].convert_to_export(self.state, self),
        #         )
        #     )
        action = self.env["ir.actions.actions"]._for_xml_id("taps_manufacturing.action_mrp_plan")
        action["domain"] = [('default_id','in',self.mapped('id'))]
        #action["context"] = {"default_item_qty": 20,"default_material_qty": 12}
        return action
    
    def _ids2str(self,field_name):
        field_data = getattr(self, field_name)
        if field_name == "ids":
            return ','.join([str(i) for i in sorted(field_data)])
        else:
            return ','.join([str(i.id) for i in sorted(field_data)])
            
    def _get_field(self,field_name):
        field_data = getattr(self, field_name)
        #raise UserError((field_name))
        return field_data
      
    
    def set_plan(self,mo_ids,plan_for_id,plan_for,material,plan_start,plan_end,plan_qty,machine_line):
        production = self.env["manufacturing.order"].browse(mo_ids)
        m_qty = 0.00
        rest_pl_q = plan_qty
        # p_len = len(production)
        # dist_qty = plan_qty / p_len
        
        addition = 0.00
        for p in production:
            if material == 'tape':
                if p.tape_con <= rest_pl_q:
                    m_qty = p.tape_con
                    rest_pl_q = rest_pl_q - p.tape_con
                else:
                    m_qty = rest_pl_q
                    rest_pl_q = 0.00
                re_pqty = m_qty 
                m_qty += p.dyeing_plan_qty
                p.update({'dyeing_plan':plan_start,'dyeing_plan_qty':m_qty,
                         'dy_rec_plan_qty':re_pqty})

            elif material == 'slider':
                if p.slider_con <= rest_pl_q:
                    m_qty = p.slider_con
                    rest_pl_q = rest_pl_q - p.slider_con
                else:
                    m_qty = rest_pl_q
                    rest_pl_q = 0.00
                re_pqty = m_qty
              
                if plan_for == 'Slider assembly':
                    m_qty += p.sli_asmbl_plan_qty
                    p.update({'sli_asmbl_plan':plan_start,'sli_asmbl_plan_qty':m_qty,'sass_rec_plan_qty':re_pqty})
                else:
                    m_qty += p.plating_plan_qty
                    p.update({'plating_plan':plan_start,'plating_plan_qty':m_qty,'pl_rec_plan_qty':re_pqty})
            
            elif material == 'top':
                if p.topwire_con <= rest_pl_q:
                    m_qty = p.topwire_con
                    rest_pl_q = rest_pl_q - p.topwire_con
                else:
                    m_qty = rest_pl_q
                    rest_pl_q = 0.00
                re_pqty = m_qty 
                m_qty += p.top_plat_plan_qty
                p.update({'top_plat_plan':plan_start,'top_plat_plan_qty':m_qty,
                         'tpl_rec_plan_qty':re_pqty})

            elif material == 'bottom':
                if p.botomwire_con <= rest_pl_q:
                    m_qty = p.botomwire_con
                    rest_pl_q = rest_pl_q - p.botomwire_con
                else:
                    m_qty = rest_pl_q
                    rest_pl_q = 0.00
                re_pqty = m_qty 
                m_qty += p.bot_plat_plan_qty
                p.update({'bot_plat_plan':plan_start,'bot_plat_plan_qty':m_qty,
                         'bpl_rec_plan_qty':re_pqty})

            elif material == 'pinbox':
                if p.pinbox_con <= rest_pl_q:
                    m_qty = p.pinbox_con
                    rest_pl_q = rest_pl_q - p.pinbox_con
                else:
                    m_qty = rest_pl_q
                    rest_pl_q = 0.00
                re_pqty = m_qty 
                m_qty += p.bot_plat_plan_qty
                p.update({'pin_plat_plan':plan_start,'pin_plat_plan_qty':m_qty,
                         'ppl_rec_plan_qty':re_pqty})            
            # if plan_for == 'dyeing':
            #     if p.tape_con < dist_qty + addition:
            #         m_qty = p.tape_con
            #         addition = (dist_qty + addition) - p.tape_con
            #     else:
            #         m_qty = dist_qty + addition
            #         addition = 0.00
            #     re_pqty = m_qty 
            #     m_qty += p.dyeing_plan_qty
            #     p.write({'dyeing_plan':plan_start,'dyeing_plan_end':plan_end,'dyeing_plan_qty':m_qty,
            #              'dy_rec_plan_qty':re_pqty})
                
    
    # ptopfinish pbotomfinish ppinboxfinish
        if material == 'tape':
            query = """ select oa_id,shade,'' as finish,'' as material,sum(dy_rec_plan_qty) as qty from manufacturing_order where id in %s and 1=%s group by oa_id,shade """
        if material == 'slider':
            query = """ select oa_id,'' as shade, finish,slidercodesfg as material,sum(pl_rec_plan_qty) as qty from manufacturing_order where id in %s and 1=%s group by oa_id,finish,slidercodesfg """
        if material == 'top':
            query = """ select oa_id,'' as shade, finish,ptopfinish as material,sum(pl_rec_plan_qty) as qty from manufacturing_order where id in %s and 1=%s group by oa_id,finish,ptopfinish """
        if material == 'bottom':
            query = """ select oa_id,'' as shade, finish,pbotomfinish as material,sum(pl_rec_plan_qty) as qty from manufacturing_order where id in %s and 1=%s group by oa_id,finish,pbotomfinish """
        if material == 'pinbox':
            query = """ select oa_id,'' as shade, finish,ppinboxfinish as material,sum(pl_rec_plan_qty) as qty from manufacturing_order where id in %s and 1=%s group by oa_id,finish,ppinboxfinish """            
            
        cr = self._cr
        cursor = self.env.cr
        cr.execute(query,[tuple(mo_ids),1])
        plan = cursor.fetchall()
        #raise UserError((plan))
        if machine_line:
            for m in machine_line:
                for p in plan:
                    qty = 0.0
                    mrp_lines = None
                    sale_lines = None
                    next_operation = None
                    mrp_line = sal_line = None
                    if material == 'tape':
                        next_operation = 'Dyeing'
                        p_q = production.filtered(lambda sol: sol.oa_id.id == p[0] and sol.shade == p[1])
                        mrp_lines = p_q._ids2str('ids')
                        sale_lines = p_q._ids2str('sale_order_line')
                        if len(p_q) > 1:
                            qty = m.material_qty
                        else:
                            mrp_line = p_q.id
                            sal_line = p_q.sale_order_line
                            qty = sum(p_q.mapped('dy_rec_plan_qty'))
                    
                    mrp_ = self.env['operation.details'].create({'mrp_lines':mrp_lines,
                                                                 'sale_lines':sale_lines,
                                                                 'mrp_line':mrp_line,
                                                                 'sale_order_line':sal_line,
                                                                 'oa_id':p[0],
                                                                 'buyer_name':p_q.buyer_name,
                                                                 'product_template_id':p_q.product_template_id.id,
                                                                 'action_date':plan_start,
                                                                 'shade':p[1],
                                                                 'finish':p[2],
                                                                 'operation_of':'plan',
                                                                 'work_center':plan_for_id,
                                                                 'operation_by':'Planning',
                                                                 'based_on':m.machine_no,
                                                                 'next_operation':next_operation,
                                                                 'qty':qty
                                                                 })


        else:
            for p in plan:
                qty = 0.0
                mrp_lines = None
                sale_lines = None
                next_operation = None
                mrp_line = sal_line = None
                
                if plan_for == 'Plating':
                    next_operation = 'Plating'
                if plan_for == 'Slider assembly':
                    next_operation = 'Slider Assembly'
                if plan_for == 'Painting':
                    next_operation = 'Painting'
                slider = top = bottom = pinbox = None
                if material == 'slider':
                    p_q = production.filtered(lambda sol: sol.oa_id.id == p[0] and sol.finish == p[2] and sol.slidercodesfg == p[3])
                    slider = p[3]
                    mrp_lines = p_q._ids2str('ids')
                    sale_lines = p_q._ids2str('sale_order_line')#.mapped('sale_order_line')
                    if len(p_q) == 1:
                        mrp_line = p_q.id
                        sal_line = p_q.sale_order_line
                        
                    if plan_for == 'Slider assembly':
                        qty = sum(p_q.mapped('sass_rec_plan_qty'))
                    else:
                        qty = sum(p_q.mapped('pl_rec_plan_qty')) 
                        
                elif material == 'top': #ptopfinish pbotomfinish ppinboxfinish
                    p_q = production.filtered(lambda sol: sol.oa_id.id == p[0] and sol.finish == p[2] and sol.ptopfinish == p[3])
                    top = p[3]
                    mrp_lines = p_q._ids2str('ids')
                    sale_lines = p_q._ids2str('sale_order_line')
                    
                    if len(p_q) == 1:
                        mrp_line = p_q.id
                        sal_line = p_q.sale_order_line
                    qty = sum(p_q.mapped('tpl_rec_plan_qty'))
                elif material == 'bottom':
                    p_q = production.filtered(lambda sol: sol.oa_id.id == p[0] and sol.finish == p[2] and sol.pbotomfinish == p[3])
                    bottom = p[3]
                    mrp_lines = p_q._ids2str('ids')
                    sale_lines = p_q._ids2str('sale_order_line')
                    if len(p_q) == 1:
                        mrp_line = p_q.id
                        sal_line = p_q.sale_order_line
                    qty = sum(p_q.mapped('bpl_rec_plan_qty'))
                elif material == 'pinbox':
                    p_q = production.filtered(lambda sol: sol.oa_id.id == p[0] and sol.finish == p[2] and sol.ppinboxfinish == p[3])
                    pinbox = p[3]
                    mrp_lines = p_q._ids2str('ids')
                    sale_lines = p_q._ids2str('sale_order_line')
                    if len(p_q) == 1:
                        mrp_line = p_q.id
                        sal_line = p_q.sale_order_line
                    qty = sum(p_q.mapped('ppl_rec_plan_qty'))
                
                mrp_line = sale_order_line = None
                mrp_ = self.env['operation.details'].create({'mrp_lines':mrp_lines,
                                                             'sale_lines':sale_lines,
                                                             'mrp_line':mrp_line,
                                                             'sale_order_line':sal_line,
                                                             'oa_id':p[0],
                                                             'buyer_name':p_q[0].buyer_name,
                                                             'product_template_id':p_q[0].product_template_id.id,
                                                             'action_date':plan_start,
                                                             'shade':p[1],
                                                             'finish':p[2],
                                                             'slidercodesfg':slider,
                                                             'top':top,
                                                             'bottom':bottom,
                                                             'pinbox':pinbox,
                                                             'operation_of':'plan',
                                                             'work_center':plan_for_id,
                                                             'operation_by':'Planning',
                                                             'based_on':material,
                                                             'next_operation':next_operation,
                                                             'qty':qty
                                                             })

    def button_requisition(self):
        self._check_company()
        action = self.env["ir.actions.actions"]._for_xml_id("taps_manufacturing.action_mrp_requisition")
        action["domain"] = [('default_id','in',self.mapped('id'))]
        return action
    
    # def button_createlot(self):
    #     self.ensure_one()
    #     self._check_company()
    #     if self.state in ("done", "to_close", "cancel"):
    #         raise UserError(
    #             _(
    #                 "Cannot split a manufacturing order that is in '%s' state.",
    #                 self._fields["state"].convert_to_export(self.state, self),
    #             )
    #         )
    #     action = self.env["ir.actions.actions"]._for_xml_id("mrp.action_split_mrp")
    #     action["context"] = {"default_mo_id": self.id,"default_product_id": self.product_id}
    #     return action

    def button_output(self):
        self.ensure_one()
        self._check_company()
        if self.state in ("done", "to_close", "cancel"):
            raise UserError(
                _(
                    "Cannot split a manufacturing order that is in '%s' state.",
                    self._fields["state"].convert_to_export(self.state, self),
                )
            )
        action = self.env["ir.actions.actions"]._for_xml_id("mrp.action_split_mrp")
        action["context"] = {"default_mo_id": self.id,"default_product_id": self.product_id}
        return action

