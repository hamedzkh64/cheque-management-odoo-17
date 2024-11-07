from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError

class Branch(models.Model):
    _name = 'cheque.branch'
    _description = 'Bank Branch'
    _inherit = ['mail.thread']

    name = fields.Char(string='Branch Name', required=True, tracking=True)
    code = fields.Char(string='Branch Code', required=True, tracking=True)
    address = fields.Text(string='Address', tracking=True)
    phone = fields.Char(string='Phone', tracking=True)
    manager = fields.Many2one('res.users', string='Branch Manager', tracking=True)
    
    # Financial settings
    default_journal_id = fields.Many2one('account.journal', string='Default Journal', tracking=True)
    transit_account_id = fields.Many2one('account.account', string='Transit Account', tracking=True)
    
    # Branch coordination
    parent_branch_id = fields.Many2one('cheque.branch', string='Parent Branch')
    child_branch_ids = fields.One2many('cheque.branch', 'parent_branch_id', string='Sub Branches')
    allowed_transfer_branch_ids = fields.Many2many(
        'cheque.branch', 
        'branch_transfer_rel', 
        'from_branch_id', 
        'to_branch_id', 
        string='Allowed Transfer Branches'
    )
    
    # Statistics
    cheque_count = fields.Integer(compute='_compute_cheque_count', string='Cheque Count')
    total_amount = fields.Monetary(compute='_compute_total_amount', string='Total Amount', 
                                 currency_field='company_currency_id')
    company_currency_id = fields.Many2one(related='company_id.currency_id', readonly=True, store=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    
    _sql_constraints = [
        ('unique_code', 'UNIQUE(code)', 'Branch code must be unique!')
    ]
    
    @api.depends('cheque_ids')
    def _compute_cheque_count(self):
        for branch in self:
            branch.cheque_count = self.env['cheque.manage'].search_count(
                [('branch_id', '=', branch.id)]
            )
            
    @api.depends('cheque_ids', 'cheque_ids.amount')
    def _compute_total_amount(self):
        for branch in self:
            cheques = self.env['cheque.manage'].search([('branch_id', '=', branch.id)])
            branch.total_amount = sum(cheques.mapped('amount'))

    @api.constrains('parent_branch_id')
    def _check_branch_hierarchy(self):
        if not self._check_recursion():
            raise ValidationError(_('Error! You cannot create recursive branch hierarchies.'))
            
    def name_get(self):
        result = []
        for branch in self:
            name = f'[{branch.code}] {branch.name}'
            result.append((branch.id, name))
        return result
