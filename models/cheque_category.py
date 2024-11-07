from odoo import fields, models, api, _

class ChequeCategory(models.Model):
    _name = 'cheque.category'
    _description = 'Categories for cheque'
    _inherit = ['mail.thread']

    name = fields.Char(string='Tag name', required=True, tracking=True)
    code = fields.Char(string='Category Code', tracking=True)
    debit_account = fields.Many2one('account.account', string='Debit account', tracking=True)
    credit_account = fields.Many2one('account.account', string='Credit account', tracking=True)
    journal_id = fields.Many2one('account.journal', string='Journal', required=True, tracking=True)
    color = fields.Integer(string='Color')
    active = fields.Boolean(default=True, tracking=True)
    
    # Additional fields for enhanced categorization
    description = fields.Text(string='Description', tracking=True)
    parent_id = fields.Many2one('cheque.category', string='Parent Category')
    child_ids = fields.One2many('cheque.category', 'parent_id', string='Child Categories')
    
    # Statistics fields
    cheque_count = fields.Integer(string='Number of Cheques', compute='_compute_cheque_count')
    total_amount = fields.Float(string='Total Amount', compute='_compute_total_amount')
    
    _sql_constraints = [
        ('unique_category_code', 'UNIQUE(code)', 'Category code must be unique.'),
        ('unique_category_name', 'UNIQUE(name)', 'Category name must be unique.')
    ]

    @api.depends('child_ids')
    def _compute_cheque_count(self):
        for category in self:
            category.cheque_count = self.env['cheque.manage'].search_count([
                ('category_id', '=', category.id)
            ])

    @api.depends('child_ids')
    def _compute_total_amount(self):
        for category in self:
            cheques = self.env['cheque.manage'].search([
                ('category_id', '=', category.id)
            ])
            category.total_amount = sum(cheques.mapped('amount'))

    @api.constrains('parent_id')
    def _check_category_recursion(self):
        if not self._check_recursion():
            raise ValueError(_('Error! You cannot create recursive categories.'))

    def name_get(self):
        result = []
        for record in self:
            if record.code:
                name = f'[{record.code}] {record.name}'
            else:
                name = record.name
            result.append((record.id, name))
        return result
