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
from datetime import timedelta

from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
import logging


_logger = logging.getLogger(__name__)


class ChequeManage(models.Model):
    _name = 'cheque.manage'
    _inherit = ['mail.thread']
    _description = 'Cheque Manage'

    @api.model
    def default_get(self, deafult_fields):
        res = super(ChequeManage, self).default_get(deafult_fields)
        Parameters = self.env['ir.config_parameter'].sudo()

        debit_account, credit_account, bank_account, journal_id = (
            int(Parameters.get_param('gt_cheque_management.debit_inc_account')),
            int(Parameters.get_param('gt_cheque_management.credit_out_account')),
            int(Parameters.get_param('gt_cheque_management.deposite_account')),
            int(Parameters.get_param('gt_cheque_management.journal_id')),
        )

        if res.get('cheq_type') == 'incoming':
            if debit_account > 0:
                res.update({'debit_account': debit_account})
                _logger.info(f"Set debit_account to {debit_account} for incoming cheque.")
        else:
            if credit_account > 0:
                res.update({'credit_account': credit_account})
                _logger.info(f"Set credit_account to {credit_account} for outgoing cheque.")

        if bank_account > 0:
            res.update({'bank_account': bank_account})
            _logger.info(f"Set bank_account to {bank_account}.")

        if journal_id > 0:
            res.update({'journal_id': journal_id})
            _logger.info(f"Set journal_id to {journal_id}.")

        return res

    @api.depends('cheq_attachment_ids')
    def _get_attach(self):
        Attachment = self.env['ir.attachment']
        for attachment in self:
            attachment.attachment_count = Attachment.search_count([('cheque_id', '=', attachment.id)])
            _logger.info(
                f"Computed attachment count for cheque ID: {attachment.id} - Count: {attachment.attachment_count}"
            )

    @api.depends('move_line_ids')
    def _journal_item_count(self):
        for item in self:
            item.journal_item_count = len(item.move_line_ids)
            _logger.info(f"Computed journal item count for cheque ID: {item.id} - Count: {item.journal_item_count}")

    seq_no = fields.Char(string='Sequence', copy=False)
    name = fields.Char(string='Name')
    attachment_count = fields.Integer(string='Attachment Count', compute='_get_attach', readonly=True, copy=False)
    journal_item_count = fields.Integer(
        string='Journal Items', compute='_journal_item_count', readonly=True, copy=False
    )
    payer = fields.Many2one('res.partner', 'Payer')
    cheque_owner_name = fields.Char(string='Cheque Owner')
    cheque_owner_national_id = fields.Char(string='Cheque Owner’s National ID')
    cheque_owner_account_number = fields.Char(string='Cheque Owner’s Account Number')
    branch_code = fields.Char(string='Branch')
    debit_account = fields.Many2one('account.account', string='Debit account')
    credit_account = fields.Many2one('account.account', string='Credit account')
    debit = fields.Monetary(default=0.0, currency_field='company_currency_id')
    credit = fields.Monetary(default=0.0, currency_field='company_currency_id')
    journal_id = fields.Many2one('account.journal', string='Journal', required=True)
    cheque_date = fields.Date(string='Cheque Date', default=fields.Date.context_today)
    cashed_date = fields.Date(string='Cashed Date', copy=False)
    return_date = fields.Date(string='Returned Date', copy=False)
    cheque_receive_date = fields.Date(string='Cheque Given/Receive Date')
    cheque_no = fields.Char(string='Cheque Number', copy=False)
    sayad_number = fields.Char(string='Sayad Number (Unique ID)', required=True, copy=False)
    amount = fields.Float(string='Amount')
    bounced = fields.Boolean(string='Bounced')
    partner_id = fields.Many2one('res.partner', 'Company')
    bank_account = fields.Many2one(
        'res.partner.bank', string='Bank Account', required=True)
    cheq_type = fields.Selection([('incoming', 'Incoming'), ('outgoing', 'Outgoing')], string='Cheque Type')
    cheq_attachment_ids = fields.One2many('ir.attachment', 'cheque_id', 'Attachment Line', copy=False)
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('register', 'Registered'),
            ('deposit', 'Deposited'),
            ('done', 'Done'),
            ('transfer', 'Transfered'),
            ('bounce', 'Bounced'),
            ('return_cashbox', 'Returned to Cash Box'),
            ('return_owner', 'Returned to Owner'),
            ('return', 'Returned'),
            ('cancel', 'Cancelled'),
        ],
        string='Status',
        default='draft',
    )
    previous_state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('register', 'Registered'),
            ('deposit', 'Deposited'),
            ('done', 'Done'),
            ('transfer', 'Transferred'),
            ('bounce', 'Bounced'),
            ('return_cashbox', 'Returned to Cash Box'),
            ('return_owner', 'Returned to Owner'),
            ('return', 'Returned'),
            ('cancel', 'Cancelled'),
        ],
        string='Previous Status',
        readonly=True,
    )
    description = fields.Text('Description')
    company_id = fields.Many2one(
        'res.company', string='Company', required=True, default=lambda self: self.env.user.company_id
    )
    company_currency_id = fields.Many2one(
        'res.currency', related='company_id.currency_id', string='Company Currency', readonly=True, store=True
    )
    move_line_ids = fields.One2many('account.move.line', 'cheque_id', readonly=True, copy=False, ondelete='restrict')

    _sql_constraints = [
        ('cheque_number_uniq', 'unique(cheque_no)', 'The Cheque Number must be unique!'),
        ('sayad_number_uniq', 'unique(sayad_number)', 'The Sayad Number must be unique!'),
        (
            'cheque_no_company_uniq',
            'unique (cheque_no,company_id)',
            'The Cheque Number of must be unique per company !',
        ),
    ]
    currency_id = fields.Many2one(
        'res.currency', string='Currency', required=True, default=lambda self: self.env.company.currency_id
    )
    cheque_book_id = fields.Many2one('cheque.book', string='Cheque Book')
    category_id = fields.Many2one('cheque.category', string='Cheque Category')

    @api.onchange('payer')
    def _onchange_payer(self):
        """Automatically set the default bank account when a payer is selected."""
        if self.payer and self.payer.bank_ids:
            self.bank_account = self.payer.bank_ids[:1].id
        else:
            self.bank_account = False

    @api.constrains('category_id')
    def _check_tag_limit(self):
        if len(self.category_id) > 1:
            raise ValidationError('You can only select one tag.')

    @api.onchange('category_id')
    def _onchange_category_id(self):
        if self.category_id:
            self.debit_account = self.category_id.debit_account if self.cheq_type == 'incoming' else self.debit_account
            self.credit_account = (
                self.category_id.credit_account if self.cheq_type == 'outgoing' else self.credit_account
            )
            self.journal_id = self.category_id.journal_id

    @api.onchange('cheq_type')
    def onchange_cheq_type(self):
        domain = {}
        if self.cheq_type:
            if self.cheq_type == 'incoming':
                domain['payer'] = [('customer_rank', '=', True)]
                _logger.info(f'Setting domain for payer to customers for cheque ID: {self.id}')
            else:
                domain['payer'] = [('supplier_rank', '=', True)]
                _logger.info(f'Setting domain for payer to suppliers for cheque ID: {self.id}')
        return {'domain': domain}

    @api.model
    def create(self, vals):
        if vals.get('cheque_book_id'):
            cheque_book = self.env['cheque.book'].browse(vals['cheque_book_id'])
            next_serial = cheque_book.get_next_serial_number()
            if next_serial:
                vals['seq_no'] = next_serial
                _logger.info(f"Assigned sequence number '{vals['seq_no']}' from cheque book ID {cheque_book.id}.")
            else:
                raise UserError('All checks in this cheque book have been used.')
        else:
            if vals.get('cheq_type') == 'incoming':
                vals['seq_no'] = self.env['ir.sequence'].next_by_code('cheque.manage.incoming') or '/'
                _logger.info(f"Assigned sequence number '{vals['seq_no']}' for incoming cheque.")
            else:
                vals['seq_no'] = self.env['ir.sequence'].next_by_code('cheque.manage.outgoing') or '/'
                _logger.info(f"Assigned sequence number '{vals['seq_no']}' for outgoing cheque.")

        cheque = super(ChequeManage, self).create(vals)

        if cheque.cheque_date:
            cron_name = f"Cheque Reminder {cheque.seq_no}"
            self.env['ir.cron'].create(
                {
                    'name': cron_name,
                    'model_id': self.env.ref('gt_cheque_management.model_cheque_manage').id,
                    'state': 'code',
                    'code': f"env['cheque.manage'].browse({cheque.id})._check_due_date_reminders()",
                    'interval_type': 'days',
                    'interval_number': 1,
                    'numbercall': -1,
                    'nextcall': cheque.cheque_date - timedelta(days=30),
                }
            )

        _logger.info(f'Cheque created with ID: {cheque.id}')
        return cheque

    @api.model
    def write(self, vals):
        if 'cheque_date' in vals and self.state == 'draft':
            self.create_cron_reminder()
        if 'state' in vals:
            for record in self:
                _logger.info(
                    f"Updating previous state for cheque ID: {record.id} from {record.state} to {vals['state']}"
                )
                vals['previous_state'] = record.state

        if 'state' in vals or 'amount' in vals or 'cheque_date' in vals:
            if self.payer:
                self.payer.calculate_weighted_average_due_date()

        return super(ChequeManage, self).write(vals)

    def revert_to_previous_stage(self):
        for cheque in self:
            _logger.info(f'Reverting cheque with ID: {cheque.id} from state: {cheque.state}')
            if cheque.previous_state:
                cheque.state = cheque.previous_state
                _logger.info(f'Cheque ID: {cheque.id} reverted to previous state: {cheque.previous_state}')
            else:
                cheque.state = 'draft'
                _logger.info(f'Cheque ID: {cheque.id} reverted to \'draft\' as no previous state was found.')

    def revert_to_draft(self):
        for cheque in self:
            _logger.info(f'Attempting to revert cheque with ID: {cheque.id} to draft state.')
            if cheque.state != 'draft':
                cheque.state = 'draft'
                _logger.info(f'Cheque ID: {cheque.id} successfully reverted to draft state.')
                for move in cheque.move_line_ids.mapped('move_id'):
                    if move.state == 'posted':
                        _logger.info(
                            f'Reverting related move with ID: {move.id} from posted to draft for cheque ID: {cheque.id}'
                        )
                        move.button_draft()
                    _logger.info(f'Unlinking all related move lines for cheque ID: {cheque.id}')
                    cheque.move_line_ids.unlink()

    def return_to_cashbox(self):
        for cheque in self:
            if cheque.state not in ['bounce', 'register', 'done']:
                _logger.warning(f"Cheque ID: {cheque.id} cannot be returned to cash box from state: {cheque.state}")
                raise UserError('Cheque cannot be returned to the cash box from its current state.')
            cheque.state = 'return_cashbox'
            _logger.info(f"Cheque ID: {cheque.id} successfully returned to cash box.")

    def return_to_owner(self):
        for cheque in self:
            if cheque.state != 'return_cashbox':
                _logger.warning(
                    f"Cheque ID: {cheque.id} cannot be returned to owner directly from state: {cheque.state}"
                )
                raise UserError('Cheque must be returned to the cash box before returning to the owner.')
            cheque.state = 'return_owner'
            _logger.info(f"Cheque ID: {cheque.id} successfully returned to owner.")

    def re_cash(self):
        for cheque in self:
            _logger.info(f'Attempting to re-cash cheque with ID: {cheque.id} in state: {cheque.state}')
            if cheque.state != 'return':
                _logger.warning(f"Cannot re-cash cheque with ID: {cheque.id} as it is not in 'return' state.")
                raise UserError('Only returned cheques can be re-cashed.')
            cheque.state = 'deposit'
            _logger.info(f'Cheque with ID: {cheque.id} successfully re-cashed.')

    def action_cashed(self):
        _logger.info(f'Opening cashing wizard')
        return {
            'res_model': 'cheque.wizard',
            'view_mode': 'form',
            'view_id': self.env.ref('gt_cheque_management.cheque_wizard_view').id,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    def action_send_to_bank(self):
        _logger.info(f'Opening deposit wizard')
        return {
            'name': _('Send Cheque to Bank'),
            'view_mode': 'form',
            'res_model': 'cheque.deposit.wizard',
            'view_id': self.env.ref('gt_cheque_management.cheque_deposit_wizard_view').id,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    def action_transfer(self):
        _logger.info(f'Opening transfer wizard')
        return {
            'res_model': 'cheque.transfer.wizard',
            'view_mode': 'form',
            'view_id': self.env.ref('gt_cheque_management.cheque_transfer_wizard_view').id,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    def abc(self):
        acc_pay = self.env['account.payment'].search([('move_line_ids', '=', self.ids)])
        for rec in acc_pay:
            if any(inv.state != 'open' for inv in rec.invoice_ids):
                _logger.warning(f"Payment ID {rec.id} cannot be processed as it has non-open invoices.")
                raise ValidationError(_('The payment cannot be processed because the invoice is not open!'))

            # Use the right sequence to set the name
            if rec.payment_type == 'transfer':
                sequence_code = 'account.payment.transfer'
            else:
                if rec.partner_type == 'customer_rank':
                    if rec.payment_type == 'inbound':
                        sequence_code = 'account.payment.customer.invoice'
                    if rec.payment_type == 'outbound':
                        sequence_code = 'account.payment.customer.refund'
                if rec.partner_type == 'supplier_rank':
                    if rec.payment_type == 'inbound':
                        sequence_code = 'account.payment.supplier.refund'
                    if rec.payment_type == 'outbound':
                        sequence_code = 'account.payment.supplier.invoice'
            rec.name = (
                self.env['ir.sequence'].with_context(ir_sequence_date=rec.payment_date).next_by_code(sequence_code)
            )
            _logger.info(f"Assigned sequence name '{rec.name}' to payment ID: {rec.id}")
            if not rec.name and rec.payment_type != 'transfer':
                _logger.error(f"Sequence for {sequence_code} is not defined in the company.")
                raise UserError(_('You have to define a sequence for %s in your company.') % (sequence_code,))

            # Create the journal entry
            amount = rec.amount * (rec.payment_type in ('outbound', 'transfer') and 1 or -1)
            move = rec._create_payment_entry(amount)
            _logger.info(f"Created journal entry with ID: {move.id} for payment ID: {rec.id}")

            # In case of a transfer, the first journal entry created debited the source liquidity account and credited
            # the transfer account. Now we debit the transfer account and credit the destination liquidity account.
            if rec.payment_type == 'transfer':
                transfer_credit_aml = move.line_ids.filtered(
                    lambda r: r.account_id == rec.company_id.transfer_account_id
                )
                transfer_debit_aml = rec._create_transfer_entry(amount)
                (transfer_credit_aml + transfer_debit_aml).reconcile()
                _logger.info(f"Transfer entries reconciled for payment ID: {rec.id}")

            rec.write({'state': 'posted', 'move_name': move.name})
            _logger.info(f"Payment ID: {rec.id} posted successfully with move name: {move.name}")

    def action_submit(self):
        if len(self.category_id) != 1:
            raise UserError('Please select category before submitting the cheque')

        category = self.category_id

        # For incoming cheques
        if self.cheq_type == 'incoming':
            credit_line = {
                'account_id': category.credit_account.id or self.payer.property_account_payable_id.id,
                'partner_id': self.payer.id,
                'name': f'{self.seq_no} - Registered',
                'debit': 0,
                'credit': self.amount,
                'date_maturity': self.cheque_date,
                'cheque_id': self.id,
            }
            debit_line = {
                'account_id': category.debit_account.id or self.debit_account.id,
                'partner_id': self.payer.id,
                'name': f'{self.seq_no} - Registered',
                'debit': self.amount,
                'credit': 0,
                'date_maturity': self.cheque_date,
                'cheque_id': self.id,
            }

        # For outgoing cheques
        else:
            credit_line = {
                'account_id': category.credit_account.id or self.credit_account.id,
                'partner_id': self.payer.id,
                'name': f'{self.seq_no} - Registered',
                'debit': 0,
                'credit': self.amount,
                'date_maturity': self.cheque_date,
                'cheque_id': self.id,
            }
            debit_line = {
                'account_id': category.debit_account.id or self.payer.property_account_receivable_id.id,
                'partner_id': self.payer.id,
                'name': f'{self.seq_no} - Registered',
                'debit': self.amount,
                'credit': 0,
                'date_maturity': self.cheque_date,
                'cheque_id': self.id,
            }

        move_vals = {
            'date': fields.Date.today(),
            'journal_id': self.journal_id.id,
            'ref': self.seq_no,
            'line_ids': [(0, 0, credit_line), (0, 0, debit_line)],
        }
        self.env['account.move'].create(move_vals)

        if self.cheq_attachment_ids:
            for attachment in self.cheq_attachment_ids:
                attachment.write({'res_id': self.id, 'res_model': 'cheque.manage'})
        return self.write({'state': 'register'})

    def action_cancel(self):
        if not self.move_line_ids:
            _logger.warning(f"Cheque ID: {self.id} cannot be canceled as it has no posted journal entries.")
            raise UserError(_('You cannot cancel a record that is not posted yet!'))
        for rec in self:
            _logger.info(f"Canceling and unlinking journal entries for cheque ID: {rec.id}")
            for move in rec.move_line_ids.mapped('move_id'):
                move.button_cancel()
                move.unlink()
            return rec.write({'state': 'cancel'})

    #    It will make reverse entry for the registerd entries

    def action_bounce(self):
        Move = self.env['account.move']
        if self.cheq_type == 'incoming':
            credit_line = {
                'account_id': self.debit_account.id,
                'partner_id': self.payer.id,
                'name': self.seq_no + '-' + 'Registered',
                'debit': 0,
                'credit': self.amount,
                'date_maturity': self.cheque_date,
                'cheque_id': self.id,
            }
            debit_line = {
                'account_id': self.payer.property_account_payable_id.id,
                'partner_id': self.payer.id,
                'name': self.seq_no + '-' + 'Registered',
                'debit': self.amount,
                'credit': 0,
                'date_maturity': self.cheque_date,
                'cheque_id': self.id,
            }
            _logger.info(f"Creating bounce journal entry for incoming cheque ID: {self.id}")
        else:
            credit_line = {
                'account_id': self.payer.property_account_receivable_id.id,
                'partner_id': self.payer.id,
                'name': self.seq_no + '-' + 'Registered',
                'debit': 0,
                'credit': self.amount,
                'date_maturity': self.cheque_date,
                'cheque_id': self.id,
            }
            debit_line = {
                'account_id': self.credit_account.id,
                'partner_id': self.payer.id,
                'name': self.seq_no + '-' + 'Registered',
                'debit': self.amount,
                'credit': 0,
                'date_maturity': self.cheque_date,
                'cheque_id': self.id,
            }
            _logger.info(f"Creating bounce journal entry for outgoing cheque ID: {self.id}")
        move_vals = {
            'date': fields.Date.today(),
            'journal_id': self.journal_id.id,
            'ref': self.seq_no,
            'line_ids': [(0, 0, credit_line), (0, 0, debit_line)],
        }
        move_id = Move.create(move_vals)
        move_id.action_post()
        _logger.info(f"Bounce journal entry with ID: {move_id.id} posted for cheque ID: {self.id}")
        return self.write({'state': 'bounce', 'bounced': True})

    def action_draft(self):
        for cheque in self:
            _logger.info(f"Setting cheque ID: {cheque.id} to draft state.")
        return self.write({'state': 'draft'})

    def action_return(self):
        if self.bounced:
            for rec in self:
                for move in rec.move_line_ids.mapped('move_id'):
                    move.button_cancel()
                    move.unlink()
                _logger.info(f"Setting state to 'return' and updating return date for bounced cheque ID: {rec.id}")
                return rec.write({'state': 'return', 'return_date': fields.Date.today()})
        else:
            Move = self.env['account.move']
            _logger.info(f"Creating return journal entry for cheque ID: {self.id}, Type: {self.cheq_type}")
            if self.cheq_type == 'incoming':
                credit_line = {
                    'account_id': self.debit_account.id,
                    'partner_id': self.payer.id,
                    'name': self.seq_no + '-' + 'Registered',
                    'debit': 0,
                    'credit': self.amount,
                    'date_maturity': self.cheque_date,
                    'cheque_id': self.id,
                }
                debit_line = {
                    'account_id': self.payer.property_account_payable_id.id,
                    'partner_id': self.payer.id,
                    'name': self.seq_no + '-' + 'Registered',
                    'debit': self.amount,
                    'credit': 0,
                    'date_maturity': self.cheque_date,
                    'cheque_id': self.id,
                }
                _logger.info(f"Incoming cheque ID: {self.id}, journal entry created for return.")
            else:
                credit_line = {
                    'account_id': self.payer.property_account_receivable_id.id,
                    'partner_id': self.payer.id,
                    'name': self.seq_no + '-' + 'Registered',
                    'debit': 0,
                    'credit': self.amount,
                    'date_maturity': self.cheque_date,
                    'cheque_id': self.id,
                }
                debit_line = {
                    'account_id': self.credit_account.id,
                    'partner_id': self.payer.id,
                    'name': self.seq_no + '-' + 'Registered',
                    'debit': self.amount,
                    'credit': 0,
                    'date_maturity': self.cheque_date,
                    'cheque_id': self.id,
                }
                _logger.info(f"Outgoing cheque ID: {self.id}, journal entry created for return.")
            move_vals = {
                'date': fields.Date.today(),
                'journal_id': self.journal_id.id,
                'ref': self.seq_no,
                'line_ids': [(0, 0, credit_line), (0, 0, debit_line)],
            }
            move_id = Move.create(move_vals)
            move_id.action_post()
            _logger.info(f"Return journal entry with ID: {move_id.id} posted for cheque ID: {self.id}")
            return self.write({'state': 'return', 'return_date': fields.Date.today()})

    def action_deposit(self):
        Move = self.env['account.move']
        if self.cheq_type == 'incoming':
            credit_line = {
                'account_id': self.debit_account.id,
                'partner_id': self.payer.id,
                'name': self.seq_no + '-' + 'Registered',
                'debit': 0,
                'credit': self.amount,
                'date_maturity': self.cheque_date,
                'cheque_id': self.id,
            }
            debit_line = {
                'account_id': self.bank_account,
                'partner_id': self.payer.id,
                'name': self.seq_no + '-' + 'Registered',
                'debit': self.amount,
                'credit': 0,
                'date_maturity': self.cheque_date,
                'cheque_id': self.id,
            }
            _logger.info(f"Creating deposit journal entry for incoming cheque ID: {self.id}")
        else:
            credit_line = {
                'account_id': self.bank_account,
                'partner_id': self.payer.id,
                'name': self.seq_no + '-' + 'Registered',
                'debit': 0,
                'credit': self.amount,
                'date_maturity': self.cheque_date,
                'cheque_id': self.id,
            }
            debit_line = {
                'account_id': self.credit_account.id,
                'partner_id': self.payer.id,
                'name': self.seq_no + '-' + 'Registered',
                'debit': self.amount,
                'credit': 0,
                'date_maturity': self.cheque_date,
                'cheque_id': self.id,
            }
            _logger.info(f"Creating deposit journal entry for outgoing cheque ID: {self.id}")
        move_vals = {
            'date': fields.Date.today(),
            'journal_id': self.journal_id.id,
            'ref': self.seq_no,
            'line_ids': [(0, 0, credit_line), (0, 0, debit_line)],
        }
        move_id = Move.create(move_vals)
        move_id.action_post()
        _logger.info(f"Deposit journal entry with ID: {move_id.id} posted for cheque ID: {self.id}")
        return self.write({'state': 'deposit'})

    def unlink(self):
        if any(bool(rec.move_line_ids) for rec in self):
            _logger.warning("Cannot delete records that are already posted.")
            raise UserError(_('You cannot delete a record that is already posted!'))
        for cheque in self:
            _logger.info(f"Preparing to delete cheque ID: {cheque.id}")
            if cheque.move_line_ids:
                for move in cheque.move_line_ids.mapped('move_id'):
                    if move.state == 'posted':
                        _logger.info(f"Setting journal entry ID: {move.id} to draft for cheque ID: {cheque.id}")
                        move.button_draft()
            self.env['revert.cheque'].create(
                {
                    'original_cheque_id': cheque.id,
                    'seq_no': cheque.seq_no,
                    'name': cheque.name,
                    'attachment_count': cheque.attachment_count,
                    'journal_item_count': cheque.journal_item_count,
                    'payer': cheque.payer.id,
                    'bank_account': cheque.bank_account,
                    'debit_account': cheque.debit_account.id,
                    'credit_account': cheque.credit_account.id,
                    'debit': cheque.debit,
                    'credit': cheque.credit,
                    'journal_id': cheque.journal_id.id,
                    'cheque_date': cheque.cheque_date,
                    'cashed_date': cheque.cashed_date,
                    'return_date': cheque.return_date,
                    'cheque_receive_date': cheque.cheque_receive_date,
                    'cheque_no': cheque.cheque_no,
                    'amount': cheque.amount,
                    'bounced': cheque.bounced,
                    'partner_id': cheque.partner_id.id,
                    'cheq_type': cheque.cheq_type,
                    'state': cheque.state,
                    'description': cheque.description,
                    'company_id': cheque.company_id.id,
                    'company_currency_id': cheque.company_currency_id.id,
                    'move_line_ids': [(6, 0, cheque.move_line_ids.ids)],
                    'deletion_date': fields.Datetime.now(),
                }
            )

        result = super(ChequeManage, self).unlink()
        _logger.info(f"Cheques with IDs: {self.ids} successfully deleted.")
        return result

    def open_payment_matching_screen(self):
        # Open reconciliation view for customers/suppliers
        move_line_id = False
        for move_line in self.move_line_ids:
            if move_line.account_id.reconcile:
                move_line_id = move_line.id
                _logger.info(f"Found move line ID: {move_line_id} for reconciliation in cheque ID: {self.id}")
                break
        action_context = {'company_ids': [self.company_id.id], 'partner_ids': [self.payer.commercial_partner_id.id]}
        if self.payer.customer_rank:
            action_context.update({'mode': 'customers_rank'})
            _logger.info(f"Setting mode to 'customers_rank' for cheque ID: {self.id}")
        elif self.payer.supplier_rank:
            action_context.update({'mode': 'suppliers_rank'})
            _logger.info(f"Setting mode to 'suppliers_rank' for cheque ID: {self.id}")
        if move_line_id:
            action_context.update({'move_line_id': move_line_id})
        # print('======action_contextaction_context========', action_context)
        _logger.info(f"Action context for cheque ID: {self.id}: {action_context}")
        return {'type': 'ir.actions.client', 'tag': 'manual_reconciliation_view', 'context': action_context}

    @staticmethod
    def button_journal_entries(self):
        _logger.info(f"Opening journal items for cheque ID(s): {self.ids}")
        return {
            'name': _('Journal Items'),
            'view_mode': 'tree,form',
            'res_model': 'account.move.line',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('cheque_id', 'in', self.ids)],
        }

    def batch_assign_to_supplier(self, supplier_id):
        supplier = self.env['res.partner'].browse(supplier_id)
        if not supplier:
            raise UserError(_('Invalid supplier'))

        for cheque in self:
            if cheque.cheq_type == 'incoming':
                cheque.write({'payer': supplier.id})
                _logger.info(f"Cheque ID {cheque.id} assigned to supplier ID {supplier.id}")
        return True

    def send_due_date_reminder(self):
        self.message_post(body="Reminder: The cheque due date is approaching!")

    @api.model
    def create_cron_reminder(self):
        for cheque in self:
            cron_name = f"Cheque Reminder - {cheque.id}"
            cron = self.env['ir.cron'].search([('name', '=', cron_name)], limit=1)

            reminder_date = cheque.calculate_reminder_date()

            cron_values = {
                'name': cron_name,
                'model_id': self.env.ref('gt_cheque_management.model_cheque_manage').id,
                'state': 'code',
                'code': f"model.send_due_date_reminder({cheque.id})",
                'nextcall': reminder_date,
                'interval_number': 1,
                'interval_type': 'days',
                'numbercall': -1,
                'active': True,
            }

            if cron:
                cron.write(cron_values)
            else:
                self.env['ir.cron'].create(cron_values)

    @api.model
    def calculate_reminder_date(self):
        if self.amount >= 500000000:
            return self.cheque_date - timedelta(days=30)
        elif 100000000 <= self.amount < 500000000:
            return self.cheque_date - timedelta(days=15)
        elif 10000000 <= self.amount < 100000000:
            return self.cheque_date - timedelta(days=7)
        else:
            return self.cheque_date - timedelta(days=2)

    def _check_due_date_reminders(self):
        """Check if a reminder is needed based on the cheque's amount and due date."""
        today = fields.Date.today()

        if self.amount >= 500000000:
            reminder_date = self.cheque_date - timedelta(days=30)
        elif 100000000 <= self.amount < 500000000:
            reminder_date = self.cheque_date - timedelta(days=15)
        elif 50000000 <= self.amount < 100000000:
            reminder_date = self.cheque_date - timedelta(days=7)
        else:
            reminder_date = self.cheque_date - timedelta(days=2)

        if today >= reminder_date:
            self.message_post(
                body=f"Reminder: Cheque {self.seq_no} with due date {self.cheque_date} is nearing. Please take action."
            )

    @api.model
    def automated_cheque_due_date_reminders(self):
        today = fields.Date.today()
        cheques = self.search([('state', '=', 'register')])

        for cheque in cheques:
            days_to_due = (cheque.cheque_date - today).days

            if cheque.amount >= 500_000_000:
                if days_to_due <= 30:
                    self._send_reminder(cheque)
            elif 100_000_000 <= cheque.amount < 500_000_000:
                if days_to_due <= 15:
                    self._send_reminder(cheque)
            elif 50_000_000 <= cheque.amount < 100_000_000:
                if days_to_due <= 7:
                    self._send_reminder(cheque)
            elif cheque.amount < 100_000_000:
                if days_to_due <= 2:
                    self._send_reminder(cheque)

    def _send_reminder(self, cheque):
        message = f"Reminder: Cheque #{cheque.seq_no} is nearing its due date."
        cheque.message_post(body=message)

    def _get_cheques_by_period(self):
        """Return cheques by specified periods: month, week, tomorrow, today."""
        today = fields.Date.today()
        start_of_week = today - timedelta(days=today.weekday())  # Start of the current week
        end_of_week = start_of_week + timedelta(days=6)  # End of the current week
        start_of_month = today.replace(day=1)  # Start of the current month
        end_of_month = (start_of_month + timedelta(days=32)).replace(day=1) - timedelta(
            days=1
        )  # End of the current month

        return {
            'today': self.search([('cheque_date', '=', today)]),
            'tomorrow': self.search([('cheque_date', '=', today + timedelta(days=1))]),
            'this_week': self.search([('cheque_date', '>=', start_of_week), ('cheque_date', '<=', end_of_week)]),
            'this_month': self.search([('cheque_date', '>=', start_of_month), ('cheque_date', '<=', end_of_month)]),
        }

    def _send_cheque_notifications(self):
        """Send notifications for cheques due based on the period."""
        cheques_by_period = self._get_cheques_by_period()

        # Notify for today
        for cheque in cheques_by_period['today']:
            cheque.message_post(body="Alert: Cheque due today.", subject="Cheque Due Alert")

        # Notify for tomorrow
        for cheque in cheques_by_period['tomorrow']:
            cheque.message_post(body="Alert: Cheque due tomorrow.", subject="Cheque Due Alert")

        # Send weekly and monthly reports
        if cheques_by_period['this_week']:
            report_body = f"Weekly Cheque Report:\n\n" + "\n".join(
                [f"Cheque #{c.id} due on {c.cheque_date}" for c in cheques_by_period['this_week']]
            )
            self.env['mail.message'].create(
                {
                    'subject': "Weekly Cheque Due Report",
                    'body': report_body,
                    'message_type': 'notification',
                    'subtype_id': self.env.ref('mail.mt_comment').id,
                    'model': 'cheque.manage',
                    'res_id': self.id,
                }
            )

        if cheques_by_period['this_month']:
            report_body = f"Monthly Cheque Report:\n\n" + "\n".join(
                [f"Cheque #{c.id} due on {c.cheque_date}" for c in cheques_by_period['this_month']]
            )
            self.env['mail.message'].create(
                {
                    'subject': "Monthly Cheque Due Report",
                    'body': report_body,
                    'message_type': 'notification',
                    'subtype_id': self.env.ref('mail.mt_comment').id,
                    'model': 'cheque.manage',
                    'res_id': self.id,
                }
            )

    def _send_email_notification(self, message):
        template_id = self.env.ref('gt_cheque_management.email_template_cheque_notification').id
        self.env['mail.template'].browse(template_id).send_mail(self.id, force_send=True)

    def send_sms_notification(self, message):
        if not self.payer.phone:
            raise UserError(
                'The partner has no phone number specified. Please add a phone number to send SMS notifications.'
            )
        sms_values = {'body': message, 'partner_id': self.payer.id, 'number': self.payer.phone}
        self.env['sms.sms'].create(sms_values).send()

    def send_email_notification(self, subject, body):
        mail_values = {
            'subject': subject,
            'body_html': body,
            'email_to': self.payer.email,
            'email_from': self.env.user.email,
        }
        mail = self.env['mail.mail'].create(mail_values).send()

    # def send_whatsapp_notification(self, message):
    #     if not self.payer.phone:
    #         raise UserError(_("Cannot send WhatsApp notification: The recipient has no phone number configured."))
    #
    #     phone_number = self.payer.phone  # Assuming `phone` is stored in E.164 format
    #     formatted_message = _("Hello, here is an update regarding your cheque: ") + message
    #
    #     # Odoo's WhatsApp send function
    #     self.env['sms.sms'].create({
    #         'partner_id': self.payer.id,
    #         'body': formatted_message,
    #         'number': phone_number,
    #     }).send_sms()

    def notify_user(self, message):
        self.send_email_notification('Cheque Alert', message)
        self.send_sms_notification(message)
        # self.send_whatsapp_notification(message)

    def _cron_cheque_due_reminder(self):
        # Select cheques due today, this week, or this month
        today_cheques = self.search([('cheque_date', '=', fields.Date.today())])
        week_cheques = self.search(
            [('cheque_date', '>=', fields.Date.today()), ('cheque_date', '<=', fields.Date.today() + timedelta(days=7))]
        )
        month_cheques = self.search(
            [
                ('cheque_date', '>=', fields.Date.today()),
                ('cheque_date', '<=', fields.Date.today() + timedelta(days=30)),
            ]
        )

        # Notify users about each due cheque
        for cheque in today_cheques:
            cheque.notify_user(_("Your cheque is due today."))

        for cheque in week_cheques:
            cheque.notify_user(_("Your cheque is due within this week."))

        for cheque in month_cheques:
            cheque.notify_user(_("Your cheque is due this month."))


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    cheque_id = fields.Many2one('cheque.manage', 'Cheque Id')


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    cheque_id = fields.Many2one('cheque.manage', 'Cheque Id')
