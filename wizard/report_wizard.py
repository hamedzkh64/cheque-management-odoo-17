# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import datetime, timedelta

class ChequeReportWizard(models.TransientModel):
    _name = 'cheque.report.wizard'
    _description = 'Advanced Cheque Report Wizard'

    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To')
    category_ids = fields.Many2many('cheque.category', string='Categories')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('register', 'Registered'),
        ('deposit', 'Deposited'),
        ('done', 'Done'),
        ('transfer', 'Transferred'),
        ('bounce', 'Bounced'),
        ('return_cashbox', 'Returned to Cash Box'),
        ('return_owner', 'Returned to Owner'),
        ('return', 'Returned'),
        ('cancel', 'Cancelled'),
    ], string='Status')
    amount_from = fields.Float(string='Amount From')
    amount_to = fields.Float(string='Amount To')
    bank_name = fields.Char(string='Bank Name')
    branch_code = fields.Char(string='Branch Code')
    include_expired = fields.Boolean(string='Include Expired Cheques')
    group_by = fields.Selection([
        ('category', 'Category'),
        ('state', 'Status'),
        ('bank', 'Bank'),
        ('month', 'Month'),
    ], string='Group By')

    def action_generate_report(self):
        domain = []
        if self.date_from:
            domain.append(('cheque_date', '>=', self.date_from))
        if self.date_to:
            domain.append(('cheque_date', '<=', self.date_to))
        if self.category_ids:
            domain.append(('category_id', 'in', self.category_ids.ids))
        if self.state:
            domain.append(('state', '=', self.state))
        if self.amount_from:
            domain.append(('amount', '>=', self.amount_from))
        if self.amount_to:
            domain.append(('amount', '<=', self.amount_to))
        if self.bank_name:
            domain.append(('cheque_book_id.bank_name', 'ilike', self.bank_name))
        if self.branch_code:
            domain.append(('branch_code', '=', self.branch_code))
        if not self.include_expired:
            domain.append(('due_date', '>=', fields.Date.today()))

        cheques = self.env['cheque.manage'].search(domain)
        
        data = {
            'ids': cheques.ids,
            'model': 'cheque.manage',
            'form': {
                'date_from': self.date_from,
                'date_to': self.date_to,
                'group_by': self.group_by,
            }
        }
        
        return self.env.ref('gt_cheque_management.action_report_cheque_advanced').report_action(self, data=data)
