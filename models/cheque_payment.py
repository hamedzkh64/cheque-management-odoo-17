from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ChequePayment(models.Model):
    _name = 'cheque.payment'
    _description = 'Cheque Payment'

    name = fields.Char(string='Payment Name', required=True)
    cheque_book_id = fields.Many2one('cheque.book', string='Cheque Book', required=True)
    cheque_id = fields.Many2one('cheque.manage', string='Cheque', domain="[('cheque_book_id', '=', cheque_book_id), ('state', '=', 'draft')]")
    recipient_id = fields.Many2one('res.partner', string='Recipient', required=True)
    amount = fields.Monetary(string="Amount", currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency', required=True,
                                  default=lambda self: self.env.company.currency_id)
    date = fields.Date(string='Payment Date', default=fields.Date.context_today, required=True)
    debit_account = fields.Many2one('account.account', string='Debit account')
    credit_account = fields.Many2one('account.account', string='Credit account')
    category_id = fields.Many2one('cheque.category', string='Cheque Category')
    journal_id = fields.Many2one('account.journal', string='Journal', required=True)
    description = fields.Text(string='Description')
    stage = fields.Selection([
        ('draft', 'Draft'),
        ('deposited', 'Deposited'),
        ('cleared', 'Cleared'),
        ('return_cashbox', 'Returned to Cashbox'),
        ('cancel', 'Cancelled')
    ], string='Stage', default='draft')

    @api.onchange('category_id')
    def _onchange_category_id(self):
        if self.category_id:
            self.debit_account = self.category_id.debit_account
            self.credit_account = self.category_id.credit_account
            self.journal_id = self.category_id.journal_id

    @api.onchange('cheque_book_id')
    def _onchange_cheque_book_id(self):
        self.cheque_id = False

    def action_confirm_payment(self):
        if not self.cheque_id:
            raise UserError(_('Please select a cheque from the cheque book.'))

        if self.cheque_id.state == 'draft':
            self.cheque_id.state = 'register'

        if self.amount == self.cheque_id.amount:
            self.cheque_id.state = 'done'
        elif self.amount < self.cheque_id.amount:
            self.cheque_id.state = 'deposit'


    def action_clear_cheque(self):
        debit_account, credit_account = self.category_id.debit_account, self.category_id.credit_account

        move_vals = {
            'date': fields.Date.today(),
            'journal_id': self.journal_id.id,
            'ref': f"Cheque Cleared - {self.name}",
            'line_ids': [
                (0, 0, {
                    'account_id': debit_account.id,
                    'partner_id': self.recipient_id.id,
                    'name': f"{self.name} - Cleared",
                    'debit': self.amount,
                    'credit': 0,
                    'cheque_id': self.id,
                }),
                (0, 0, {
                    'account_id': credit_account.id,
                    'partner_id': self.recipient_id.id,
                    'name': f"{self.name} - Cleared",
                    'debit': 0,
                    'credit': self.amount,
                    'cheque_id': self.id,
                })
            ]
        }
        move_id = self.env['account.move'].create(move_vals)
        move_id.action_post()

        self.write({'stage': 'cleared'})

    def send_to_bank(self):
        if self.stage != 'draft':
            raise UserError('Cheque must be in draft stage to be sent to the bank.')
        self.stage = 'deposited'


    def action_bounce(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Bounce Cheque',
            'view_mode': 'form',
            'res_model': 'cheque.bounce.wizard',
            'target': 'new',
            'context': {'default_cheque_payment_id': self.id},
        }
