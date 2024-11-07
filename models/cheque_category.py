from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

class ChequeCategory(models.Model):
    _name = 'cheque.category'
    _description = 'Categories for cheque'
    _inherit = ['mail.thread']

    name = fields.Char(string='Tag name', required=True, tracking=True)
    code = fields.Char(string='Category Code', required=True, tracking=True)
    
    # Enhanced account specifications
    account_type = fields.Selection([
        ('receivable', 'Receivable'),
        ('payable', 'Payable'),
        ('income', 'Income'),
        ('expense', 'Expense'),
        ('other', 'Other')
    ], string='Account Type', required=True, tracking=True)
    
    debit_account = fields.Many2one('account.account', string='Debit Account',
                                  required=True, tracking=True,
                                  domain="[('account_type', '=', account_type)]")
    credit_account = fields.Many2one('account.account', string='Credit Account',
                                   required=True, tracking=True,
                                   domain="[('account_type', '=', account_type)]")
    
    # Enhanced journal settings
    journal_id = fields.Many2one('account.journal', string='Journal', required=True, tracking=True)
    journal_type = fields.Selection([
        ('sale', 'Sales'),
        ('purchase', 'Purchase'),
        ('cash', 'Cash'),
        ('bank', 'Bank'),
        ('general', 'Miscellaneous')
    ], string='Journal Type', required=True, tracking=True)
    
    # Additional fields for enhanced categorization
    description = fields.Text(string='Description', tracking=True)
    active = fields.Boolean(default=True, tracking=True)
    color = fields.Integer(string='Color')
    
    # Hierarchical structure
    parent_id = fields.Many2one('cheque.category', string='Parent Category')
    child_ids = fields.One2many('cheque.category', 'parent_id', string='Child Categories')
    
    # Automated entry settings
    auto_post_entries = fields.Boolean(string='Auto Post Entries', default=True,
                                     help='Automatically post accounting entries when using this category')
    generate_analytic_lines = fields.Boolean(string='Generate Analytic Lines', default=False,
                                           help='Generate analytical accounting entries')
    analytic_account_id = fields.Many2one('account.analytic.account', string='Default Analytic Account')
    
    # Statistics and tracking
    total_transactions = fields.Integer(string='Total Transactions', compute='_compute_statistics')
    total_amount = fields.Monetary(string='Total Amount', compute='_compute_statistics',
                                 currency_field='company_currency_id')
    company_currency_id = fields.Many2one(related='company_id.currency_id', readonly=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)

    _sql_constraints = [
        ('unique_category_code', 'UNIQUE(code)', 'Category code must be unique.'),
        ('unique_category_name', 'UNIQUE(name)', 'Category name must be unique.')
    ]

    @api.constrains('parent_id')
    def _check_category_recursion(self):
        if not self._check_recursion():
            raise ValidationError(_('Error! You cannot create recursive categories.'))

    @api.depends('child_ids')
    def _compute_statistics(self):
        for category in self:
            cheques = self.env['cheque.manage'].search([
                ('category_id', '=', category.id)
            ])
            category.total_transactions = len(cheques)
            category.total_amount = sum(cheques.mapped('amount'))

    @api.onchange('journal_type')
    def _onchange_journal_type(self):
        """Update journal domain based on selected type"""
        if self.journal_type:
            return {'domain': {'journal_id': [('type', '=', self.journal_type)]}}

    def generate_accounting_entries(self, cheque_id, amount):
        """Generate automated accounting entries for a cheque"""
        self.ensure_one()
        cheque = self.env['cheque.manage'].browse(cheque_id)
        
        if not cheque:
            raise ValidationError(_('Cheque not found.'))

        move_vals = {
            'date': fields.Date.today(),
            'journal_id': self.journal_id.id,
            'ref': f'Cheque: {cheque.seq_no}',
            'line_ids': [
                (0, 0, {
                    'account_id': self.debit_account.id,
                    'debit': amount,
                    'credit': 0.0,
                    'name': f'Cheque payment - {self.name}',
                    'partner_id': cheque.payer.id,
                    'analytic_account_id': self.analytic_account_id.id if self.generate_analytic_lines else False,
                }),
                (0, 0, {
                    'account_id': self.credit_account.id,
                    'debit': 0.0,
                    'credit': amount,
                    'name': f'Cheque payment - {self.name}',
                    'partner_id': cheque.payer.id,
                    'analytic_account_id': self.analytic_account_id.id if self.generate_analytic_lines else False,
                })
            ]
        }
        
        move = self.env['account.move'].create(move_vals)
        if self.auto_post_entries:
            move.action_post()
            _logger.info(f'Auto-posted accounting entry for cheque {cheque.seq_no} in category {self.name}')
        
        return move

    def name_get(self):
        """Override name_get to include the category code"""
        result = []
        for record in self:
            name = f'[{record.code}] {record.name}' if record.code else record.name
            result.append((record.id, name))
        return result
