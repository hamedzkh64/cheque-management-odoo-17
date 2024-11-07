# -*- coding: utf-8 -*-
##############################################################################
#
#    Globalteckz Pvt Ltd
#    Copyright (C) 2013-Today(www.globalteckz.com).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


from odoo import api, fields, models


class ChequeWizard(models.TransientModel):
    _name = 'cheque.wizard'
    _description = 'Cheque Wizard'
    
    cheque_date = fields.Date(string='Cheque Date')
    

    def cash_submit(self):  
        cheque_inc = self.env['cheque.manage'].search([])
        cheque_inc.cheque_date = self.cheque_date
        return cheque_inc.write({'state': 'done'})
    
    
class ChequeTransferWizard(models.TransientModel):
    _name = 'cheque.transfer.wizard'
    _description = 'Cheque Transfer'
    
    transfer_date = fields.Date(string='Transferred Date')
    contact = fields.Many2one('res.partner', 'Contact')
    

    def transfer_submit(self):  
        cheque_inc = self.env['cheque.manage'].search([])
        return cheque_inc.write({'state': 'transfer'})
    
                    
class ChequeOutgoingWizard(models.TransientModel):
    _name = 'cheque.outgoing.wizard'
    _description = 'Cheque Outgoing Wizard'
    
    cheque_date = fields.Date(string='Cheque Date')
    bank_acc = fields.Many2one('res.partner.bank',  'Bank Account', domain="[('partner_id', '=', company_id)]", required=True)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )

    category_id = fields.Many2one(
        'cheque.category',
        string='Category',
        required=True,
        help='Category used to pre-define debit and credit accounts.'
    )

    def cash_out_submit(self):
        cheque_id = self.env[self._context.get('active_model')].browse(self._context.get('active_ids'))
        debit_account, credit_account = self.category_id.debit_account, self.category_id.credit_account
        if cheque_id.cheq_type=='incoming':
            credit_line = {
                'account_id': credit_account.id,
                'partner_id': cheque_id.payer.id,
                'name': cheque_id.seq_no+'-'+'Registered',
                'debit': 0,
                'credit': cheque_id.amount,
                'date_maturity': cheque_id.cheque_date,
                'cheque_id': cheque_id.id,
            }
            debit_line = {
                'account_id': debit_account.id,
                'partner_id': cheque_id.payer.id,
                'name': cheque_id.seq_no+'-'+'Registered',
                'debit': cheque_id.amount,
                'credit': 0,
                'date_maturity': cheque_id.cheque_date,
                'cheque_id': cheque_id.id,
            }
        else:
            credit_line = {
                'account_id': credit_account.id,
                'partner_id': cheque_id.payer.id,
                'name': cheque_id.seq_no+'-'+'Registered',
                'debit': 0,
                'credit': cheque_id.amount,
                'date_maturity': cheque_id.cheque_date,
                'cheque_id': cheque_id.id,
            }
            debit_line = {
                'account_id': debit_account.id,
                'partner_id': cheque_id.payer.id,
                'name': cheque_id.seq_no+'-'+'Registered',
                'debit': cheque_id.amount,
                'credit': 0,
                'date_maturity': cheque_id.cheque_date,
                'cheque_id': cheque_id.id,
            }
        move_vals = {
            'date': fields.Date.today(),
            'journal_id': cheque_id.journal_id.id,
            'ref': cheque_id.seq_no,
            'line_ids': [(0, 0, credit_line), (0, 0, debit_line)]
        }
        move_id = self.env['account.move'].create(move_vals)
        move_id.action_post()
        cheque_id.write({'cashed_date': self.cheque_date, 'state': 'done'})
        return True


class ChequeDepositWizard(models.TransientModel):
    _name = 'cheque.deposit.wizard'
    _description = 'Cheque Deposit'

    cheque_id = fields.Many2one('cheque.manage', string='Cheque', required=True)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )
    bank_acc = fields.Many2one('res.partner.bank', 'Bank Account', domain='[("partner_id", "=", company_id)]', required=True)
    category_id = fields.Many2one(
        'cheque.category',
        string='Category',
        required=True,
        help='Category used to pre-define debit and credit accounts.'
    )
    debit_account_id = fields.Many2one('account.account', string='Debit Account', readonly=True)
    credit_account_id = fields.Many2one('account.account', string='Credit Account', readonly=True)

    @api.onchange('category_id')
    def _onchange_category_id(self):
        """ Set debit and credit accounts based on selected category """
        if self.category_id:
            self.debit_account_id = self.category_id.debit_account
            self.credit_account_id = self.category_id.credit_account

    def confirm_deposit(self):
        self.cheque_id.write({
            'state': 'deposit',
            'bank_account': self.bank_acc.id,
            'category_id': self.category_id.id
        })
        return {'type': 'ir.actions.act_window_close'}


class ChequeBounceWizard(models.TransientModel):
    _name = 'cheque.bounce.wizard'
    _description = 'Cheque Bounce Wizard'

    cheque_payment_id = fields.Many2one('cheque.payment', string='Cheque Payment')
    journal_id = fields.Many2one(related='cheque_payment_id.journal_id', string='Journal', readonly=True)
    name = fields.Char(related='cheque_payment_id.name', string='Reference', readonly=True)
    amount = fields.Monetary(related='cheque_payment_id.amount', readonly=True, currency_field='currency_id')
    currency_id = fields.Many2one(related='cheque_payment_id.currency_id', readonly=True)
    recipient_id = fields.Many2one(related='cheque_payment_id.recipient_id', string='Partner', readonly=True)
    bounce_action = fields.Selection([('return_cashbox', 'Return to Cashbox'), ('cancel', 'Cancel')],
                                     string='Bounce Action', required=True)
    category_id = fields.Many2one('cheque.category', string='Category', required=True)

    def confirm_bounce(self):
        if self.bounce_action == 'return_cashbox':
            self.cheque_payment_id.write({'stage': 'return_cashbox'})
        elif self.bounce_action == 'cancel':
            self.cheque_payment_id.write({'stage': 'cancel'})

        debit_account, credit_account = self.category_id.debit_account.id, self.category_id.credit_account.id

        move_vals = {
            'date': fields.Date.today(),
            'journal_id': self.journal_id.id,
            'ref': self.name,
            'line_ids': [
                (0, 0, {
                    'account_id': debit_account,
                    'debit': self.amount,
                    'credit': 0.0,
                    'partner_id': self.recipient_id.id,
                }),
                (0, 0, {
                    'account_id': credit_account,
                    'debit': 0.0,
                    'credit': self.amount,
                    'partner_id': self.recipient_id.id,
                }),
            ]
        }

        move = self.env['account.move'].create(move_vals)
        move.action_post()


class ChequeReturnWizard(models.TransientModel):
    _name = 'cheque.return.wizard'
    _description = 'Cheque Return Wizard'

    cheque_spend_id = fields.Many2one('cheque.spend', string='Cheque Spend')
    return_option = fields.Selection([
        ('cashbox', 'Return to Cashbox'),
        ('customer', 'Return to Customer')
    ], string='Return Option', required=True)
    return_category_id = fields.Many2one('cheque.category', string='Category', required=True)

    def confirm_return(self):
        for cheque in self.cheque_spend_id.cash_box_cheque_ids:
            if self.return_option == 'cashbox':
                cheque.write({'state': 'return_cashbox'})
            else:
                cheque.write({'state': 'return_owner'})

            # Create journal entries for accounting
            debit_account = self.return_category_id.debit_account.id
            credit_account = self.return_category_id.credit_account.id
            move_vals = {
                'date': fields.Date.today(),
                'journal_id': self.cheque_spend_id.journal_id.id,
                'ref': self.cheque_spend_id.name,
                'line_ids': [
                    (0, 0,
                     {'account_id': debit_account, 'debit': cheque.amount, 'credit': 0, 'partner_id': cheque.payer.id}),
                    (0, 0, {'account_id': credit_account, 'debit': 0, 'credit': cheque.amount,
                            'partner_id': cheque.payer.id}),
                ]
            }
            self.env['account.move'].create(move_vals).action_post()
