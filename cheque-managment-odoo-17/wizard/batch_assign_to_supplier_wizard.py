from odoo import models, fields, _
from odoo.exceptions import UserError


class BatchAssignToSupplierWizard(models.TransientModel):
    _name = 'batch.assign.to.supplier.wizard'
    _description = 'Batch Assign to Supplier'

    supplier_id = fields.Many2one('res.partner', string='Supplier', required=True)
    cheque_ids = fields.Many2many('cheque.manage', string="Cheques")
    cheque_date = fields.Date(string='Cheque Date')
    bank_acc = fields.Many2one('account.account', 'Bank Account')

    def action_assign(self):
        if not self.cheque_ids:
            raise UserError(_('Please select at least one cheque.'))

        self.cheque_ids.batch_assign_to_supplier(self.supplier_id.id)
