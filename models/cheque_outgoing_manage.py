#
#    Globalteckz Pvt Ltd
#    Copyright (C) 2013-Today(www.globalteckz.com).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version
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

from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)

class AccountPaymentMethod(models.Model):
    _inherit = 'account.payment.method'
    
    payment_type = fields.Selection([
        ('inbound', 'Inbound'),
        ('outbound', 'Outbound'),
        ('cheque', 'Cheque'),
        ('bank_transfer', 'Bank Transfer'),
        ('credit_card', 'Credit Card'),
        ('debit_card', 'Debit Card'),
        ('digital_wallet', 'Digital Wallet'),
        ('cash', 'Cash')
    ], required=True)
    
    payment_processor_id = fields.Many2one('payment.processor', string='Payment Processor')
    requires_bank_account = fields.Boolean(string='Requires Bank Account')
    requires_card_info = fields.Boolean(string='Requires Card Information')
    supports_refund = fields.Boolean(string='Supports Refund', default=True)
    
    @api.onchange('payment_type')
    def _onchange_payment_type(self):
        self.requires_bank_account = self.payment_type in ['bank_transfer', 'cheque']
        self.requires_card_info = self.payment_type in ['credit_card', 'debit_card']

class AccountPayment(models.Model):
    _inherit = 'account.payment'
    
    payment_processor_id = fields.Many2one('payment.processor', string='Payment Processor')
    processing_fee = fields.Monetary(string='Processing Fee', compute='_compute_processing_fee')
    card_number = fields.Char(string='Card Number')
    card_holder = fields.Char(string='Card Holder')
    card_expiry = fields.Char(string='Card Expiry')
    bank_account_id = fields.Many2one('res.partner.bank', string='Bank Account')
    
    @api.depends('payment_processor_id', 'amount')
    def _compute_processing_fee(self):
        for payment in self:
            if payment.payment_processor_id:
                payment.processing_fee = payment.payment_processor_id.calculate_processing_fee(payment.amount)
            else:
                payment.processing_fee = 0.0

    @api.depends('cheque_out_attach_line')
    def _get_attach(self):
        for record in self:
            initial_count = record.attachment_count
            record.attachment_count += len(record.cheque_out_attach_line.ids)
            _logger.info(
                f"Updated attachment count for cheque ID: {record.id} - Initial: {initial_count}, New: {record.attachment_count}")

    attachment_count = fields.Integer(string='Attachment Count', compute='_get_attach', readonly=True)
    cheque_date = fields.Date(string='Cheque Date')
    cheque_receive_date = fields.Date(string='Cheque Receive Date')
    cheque_no = fields.Char(string='Cheque Number')
    state_new = fields.Selection([
    ('draft', 'Draft'),
    ('register', 'Registered'),
    ('bounce', 'Bounced'),
    ('return', 'Returned'),
    ('done', 'Done'),
    ('cancel', 'Cancel'),
    ], string='Status', default='draft')
    description = fields.Text('Description')
    cheque_out_attach_line = fields.One2many('cheque.outgoing.attach', 'cheque_out_id', string='Bank account')
    credit_account_id = fields.Many2one('account.account', string='Credit Account')
    debit_account_id = fields.Many2one('account.account', string='Debit Account')
    category_id = fields.Many2one('cheque.category', string = "Cheque category")

    @api.onchange('category_id')
    def _onchange_category_id(self):
        if self.category_id and self.payment_type == 'inbound':
            self.debit_account_id = self.category_id.debit_account
        elif self.category_id and self.payment_type == 'outbound':
            self.credit_account_id = self.category_id.credit_account

    def action_post(self):
        for rec in self:
            # For non-cheque payments, process through payment processor
            if rec.payment_method_id.payment_type != 'cheque' and rec.payment_processor_id:
                rec.payment_processor_id.process_payment(rec)
            # For cheque payments, use existing cheque processing logic
            elif rec.payment_method_id.payment_type == 'cheque':
                return super(AccountPayment, self).action_post()
            else:
                raise UserError(_('Please select a payment processor for non-cheque payments.'))

    def action_cashed(self):
        _logger.info(f"Opening cashing wizard for cheque ID(s): {self.ids}")
        return {
            'res_model': 'cheque.outgoing.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': self.env.ref('gt_cheque_management.cheque_outgoing_wizard_view').id,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }
    
    def action_submit(self):
        """ Create the journal items for the payment and update the payment's state to 'posted'.
            A journal entry is created containing an item in the source liquidity account (selected journal's default_debit or default_credit)
            and another in the destination reconcilable account (see _compute_destination_account_id).
            If invoice_ids is not empty, there will be one reconcilable move line per invoice to reconcile with.
            If the payment is a transfer, a second journal entry is created in the destination journal to receive money from the transfer account.
        """
        for rec in self:
            if rec.state != 'draft':
                _logger.warning(f"Payment ID: {rec.id} is not in draft state and cannot be posted.")
                raise UserError(_('Only a draft payment can be posted.'))

            if any(inv.state != 'open' for inv in rec.invoice_ids):
                _logger.warning(f"Payment ID: {rec.id} cannot be processed because some invoices are not open.")
                raise ValidationError(_('The payment cannot be processed because the invoice is not open!'))

            # keep the name in case of a payment reset to draft
            if not rec.name:
                # Use the right sequence to set the name
                if rec.payment_type == 'transfer':
                    sequence_code = 'account.payment.transfer'
                else:
                    if rec.partner_type == 'customer':
                        if rec.payment_type == 'inbound':
                            sequence_code = 'account.payment.customer.invoice'
                        if rec.payment_type == 'outbound':
                            sequence_code = 'account.payment.customer.refund'
                    if rec.partner_type == 'supplier':
                        if rec.payment_type == 'inbound':
                            sequence_code = 'account.payment.supplier.refund'
                        if rec.payment_type == 'outbound':
                            sequence_code = 'account.payment.supplier.invoice'
                rec.name = self.env['ir.sequence'].with_context(ir_sequence_date=rec.payment_date).next_by_code(sequence_code)
                if not rec.name and rec.payment_type != 'transfer':
                    _logger.error(f"Sequence for {sequence_code} is not defined in the company.")
                    raise UserError(_('You have to define a sequence for %s in your company.') % (sequence_code,))
                _logger.info(f"Assigned sequence name '{rec.name}' to payment ID: {rec.id}")

            # Create the journal entry
            amount = rec.amount * (rec.payment_type in ('outbound', 'transfer') and 1 or -1)
            move = rec._create_payment_entry(amount)
            _logger.info(f"Journal entry created for payment ID: {rec.id} with move ID: {move.id}")

            # In case of a transfer, the first journal entry created debited the source liquidity account and credited
            # the transfer account. Now we debit the transfer account and credit the destination liquidity account.
            if rec.payment_type == 'transfer':
                transfer_credit_aml = move.line_ids.filtered(lambda r: r.account_id == rec.company_id.transfer_account_id)
                transfer_debit_aml = rec._create_transfer_entry(amount)
                (transfer_credit_aml + transfer_debit_aml).reconcile()
                _logger.info(f"Transfer reconciliation completed for payment ID: {rec.id}")

            rec.write({'state': 'posted', 'move_name': move.name})
            _logger.info(f"Payment ID: {rec.id} has been posted with journal entry name: {move.name}")

        return True

    def button_journal_entries(self):
        _logger.info(f"Opening journal items for payment ID(s): {self.ids}")
        return {
            'name': _('Journal Items'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.move.line',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('payment_id', 'in', self.ids)],
        }

    def action_bounce(self):
        _logger.info(f"Setting state to 'bounce' for cheque ID(s): {self.ids}")
        return self.write({'state': 'bounce'})
    
    def action_draft(self):
        _logger.info(f"Reverting cheque ID(s): {self.ids} to draft state.")
        return self.write({'state': 'draft'})
    
    def action_return(self):
        _logger.info(f"Setting state to 'return' for cheque ID(s): {self.ids}")
        return self.write({'state': 'return'})
    
    def action_deposit(self):
        _logger.info(f"Setting state to 'deposit' for cheque ID(s): {self.ids}")
        return self.write({'state': 'deposit'})
    
    def action_transfer(self):
        _logger.info(f"Setting state to 'transfer' for cheque ID(s): {self.ids}")
        return self.write({'state': 'transfer'})

class ChequeOutgoingAttach(models.Model):
    _name = 'cheque.outgoing.attach'
    _description = 'Cheque Outgoing Attach'

    cheque_out_id = fields.Many2one('account.payment', string='Cheque Attach')
    name = fields.Char(string='Name')
    filename = fields.Binary(string='File Name')
    resource_model = fields.Char(string='Resouce Model')
    resource_field = fields.Char(string='Resource Field')
    resource_id = fields.Char(string='Resource ID')
    created_by = fields.Many2one('res.users', 'Created by')
    created_on = fields.Datetime('Created on')