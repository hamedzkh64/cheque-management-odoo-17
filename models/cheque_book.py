from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ChequeBook(models.Model):
    _name = 'cheque.book'
    _description = 'Cheque Book Management'

    name = fields.Char(string='Name', required=True)
    bank_id = fields.Many2one('res.bank', string='Bank', required=True)
    account_id = fields.Many2one('account.account', string='Bank Account', required=True)
    start_number = fields.Integer(string='Start Number', required=True)
    end_number = fields.Integer(string='End Number', required=True)
    current_number = fields.Integer(string='Current Number', compute='_compute_current_number', store=True)
    total_leaves = fields.Integer(string='Total Leaves', compute='_compute_total_leaves')
    remaining_leaves = fields.Integer(string='Remaining Leaves', compute='_compute_remaining_leaves')
    branch_id = fields.Many2one('branch.model', string='Branch')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

    @api.depends('start_number', 'end_number')
    def _compute_total_leaves(self):
        for book in self:
            book.total_leaves = book.end_number - book.start_number + 1 if book.start_number and book.end_number else 0

    @api.depends('cheque_ids.state')
    def _compute_current_number(self):
        for book in self:
            used_cheques = self.env['cheque.manage'].search([
                ('cheque_book_id', '=', book.id),
                ('state', '!=', 'cancel')
            ], order='cheque_number DESC', limit=1)
            book.current_number = used_cheques.cheque_number if used_cheques else book.start_number - 1

    @api.depends('total_leaves', 'cheque_ids.state')
    def _compute_remaining_leaves(self):
        for book in self:
            used_cheques = self.env['cheque.manage'].search_count([
                ('cheque_book_id', '=', book.id),
                ('state', '!=', 'cancel')
            ])
            book.remaining_leaves = book.total_leaves - used_cheques

    @api.constrains('start_number', 'end_number')
    def _check_numbers(self):
        for book in self:
            if book.start_number and book.end_number:
                if book.start_number >= book.end_number:
                    raise UserError(_('Start number must be less than end number'))

    def generate_leaves(self):
        """Generate cheque leaves for the cheque book"""
        self.ensure_one()
        ChequeManage = self.env['cheque.manage']
        
        for number in range(self.start_number, self.end_number + 1):
            existing_cheque = ChequeManage.search([
                ('cheque_book_id', '=', self.id),
                ('cheque_number', '=', str(number))
            ])
            if not existing_cheque:
                ChequeManage.create({
                    'cheque_book_id': self.id,
                    'cheque_number': str(number),
                    'bank_id': self.bank_id.id,
                    'account_id': self.account_id.id,
                    'branch_id': self.branch_id.id,
                    'state': 'draft'
                })
