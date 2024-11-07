from odoo import api, fields, models


class ChequeCategory(models.Model):
    _name = 'cheque.category'
    _description = 'Cheque Category'
    _parent_store = True
    _rec_name = 'complete_name'
    _order = 'complete_name'

    name = fields.Char(string='Category Name', required=True)
    complete_name = fields.Char(string='Complete Name', compute='_compute_complete_name', store=True)
    parent_id = fields.Many2one('cheque.category', string='Parent Category', index=True, ondelete='cascade')
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many('cheque.category', 'parent_id', string='Child Categories')
    description = fields.Text(string='Description')
    active = fields.Boolean(default=True)
    
    debit_account = fields.Many2one('account.account', string='Default Debit Account')
    credit_account = fields.Many2one('account.account', string='Default Credit Account')
    journal_id = fields.Many2one('account.journal', string='Default Journal')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for category in self:
            if category.parent_id:
                category.complete_name = '%s / %s' % (category.parent_id.complete_name, category.name)
            else:
                category.complete_name = category.name

    @api.constrains('parent_id')
    def _check_hierarchy(self):
        if not self._check_recursion():
            raise models.ValidationError('Error! You cannot create recursive categories.')

    def name_get(self):
        result = []
        for record in self:
            result.append((record.id, record.complete_name))
        return result
