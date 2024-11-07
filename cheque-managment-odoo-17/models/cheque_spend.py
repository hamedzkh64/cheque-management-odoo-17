from odoo import api, fields, models


class ChequeSpend(models.Model):
    _name = 'cheque.spend'
    _description = 'Cheque Spend from Cashbox'

    name = fields.Char(string='Spend Name', required=True)
    recipient_id = fields.Many2one('res.partner', string='Recipient')
    cash_box_cheque_ids = fields.Many2many(
        'cheque.manage', 'cashbox_cheque_spend_rel', 'spend_id', 'cheque_id',
        string='Available Cashbox Cheques', domain="[('cheq_type', '=', 'incoming'), ('state', '=', 'done')]"
    )
    amount = fields.Float(string='Total Amount', compute='_compute_total_amount')
    category_id = fields.Many2one('cheque.category', string='Cheque Category')
    journal_id = fields.Many2one('account.journal', string='Journal', required=True)
    # category_id = fields.Many2one('cheque.category', string='Category', compute='_compute_category_id', store=True)
    #
    # @api.depends('cash_box_cheque_ids')
    # def _compute_category_id(self):
    #     for record in self:
    #         if record.cash_box_cheque_ids:
    #             record.category_id = record.cash_box_cheque_ids[0].category_id
    #         else:
    #             record.category_id = False


    @api.depends('cash_box_cheque_ids')
    def _compute_total_amount(self):
        for record in self:
            record.amount = sum(cheque.amount for cheque in record.cash_box_cheque_ids)

    def action_open_return_wizard(self):
        """ Open wizard for return process """
        return {
            'name': 'Return Cheque',
            'type': 'ir.actions.act_window',
            'res_model': 'cheque.return.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_cheque_spend_id': self.id,
                'default_return_option': 'cashbox',
            }
        }
