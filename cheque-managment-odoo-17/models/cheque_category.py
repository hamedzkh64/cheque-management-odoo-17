from odoo import fields, models


class ChequeCategory(models.Model):
    _name = 'cheque.category'
    _description = 'Categories for cheque'

    name=fields.Char(string='Tag name', required=True)
    debit_account = fields.Many2one('account.account', string='Debit account')
    credit_account = fields.Many2one('account.account', string='Credit account')
    journal_id = fields.Many2one('account.journal', string='Journal', required=True)
    color = fields.Integer(string='Color')

    _sql_constraints = [
        ('unique_property_tag_name', 'UNIQUE(name)', 'Category name must be unique.')
    ]
