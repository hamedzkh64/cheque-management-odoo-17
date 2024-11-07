from odoo import api, fields, models, _
from odoo.exceptions import UserError


class Branch(models.Model):
    _name = 'branch.model'
    _description = 'Branch Management'

    name = fields.Char(string='Branch Name', required=True)
    code = fields.Char(string='Branch Code', required=True)
    parent_id = fields.Many2one('branch.model', string='Parent Branch')
    child_ids = fields.One2many('branch.model', 'parent_id', string='Child Branches')
    manager_id = fields.Many2one('res.users', string='Branch Manager')
    address = fields.Text(string='Branch Address')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Currency', related='company_id.currency_id')

    _sql_constraints = [
        ('unique_branch_code', 'unique(code)', 'Branch code must be unique!')
    ]

    @api.constrains('parent_id')
    def _check_hierarchy(self):
        if not self._check_recursion():
            raise UserError(_('Error! You cannot create recursive branch hierarchy.'))

    def name_get(self):
        result = []
        for branch in self:
            name = branch.name
            if branch.code:
                name = f'[{branch.code}] {name}'
            result.append((branch.id, name))
        return result
