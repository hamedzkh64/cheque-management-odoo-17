from datetime import timedelta
from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)

class ChequeManage(models.Model):
    _name = 'cheque.manage'
    _inherit = ['mail.thread']
    _description = 'Cheque Manage'
    
    # Enhanced fields for better tracking
    seq_no = fields.Char(string='Sequence', copy=False, readonly=True)
    name = fields.Char(string='Name', tracking=True)
    attachment_count = fields.Integer(string='Attachment Count', compute='_get_attach', readonly=True, copy=False)
    journal_item_count = fields.Integer(string='Journal Items', compute='_journal_item_count', readonly=True, copy=False)
    
    # Enhanced payer and owner information
    payer = fields.Many2one('res.partner', 'Payer', tracking=True)
    cheque_owner_name = fields.Char(string='Cheque Owner', tracking=True)
    cheque_owner_national_id = fields.Char(string='Cheque Owner’s National ID', tracking=True)
    cheque_owner_account_number = fields.Char(string='Cheque Owner’s Account Number', tracking=True)
    branch_code = fields.Char(string='Branch', tracking=True)
    
    # Financial fields
    debit_account = fields.Many2one('account.account', string='Debit account', tracking=True)
    credit_account = fields.Many2one('account.account', string='Credit account', tracking=True)
    debit = fields.Monetary(default=0.0, currency_field='company_currency_id', tracking=True)
    credit = fields.Monetary(default=0.0, currency_field='company_currency_id', tracking=True)
    journal_id = fields.Many2one('account.journal', string='Journal', required=True, tracking=True)
    
    # Enhanced date tracking
    cheque_date = fields.Date(string='Cheque Date', default=fields.Date.context_today, tracking=True)
    cashed_date = fields.Date(string='Cashed Date', copy=False, tracking=True)
    return_date = fields.Date(string='Returned Date', copy=False, tracking=True)
    cheque_receive_date = fields.Date(string='Cheque Given/Receive Date', tracking=True)
    due_date = fields.Date(string='Due Date', compute='_compute_due_date', store=True)
    
    # Enhanced cheque information
    cheque_no = fields.Char(string='Cheque Number', copy=False, tracking=True)
    sayad_number = fields.Char(string='Sayad Number (Unique ID)', required=True, copy=False, tracking=True)
    amount = fields.Float(string='Amount', tracking=True)
    bounced = fields.Boolean(string='Bounced', tracking=True)
    bounce_reason = fields.Selection([
        ('insufficient_funds', 'Insufficient Funds'),
        ('account_closed', 'Account Closed'),
        ('stop_payment', 'Stop Payment'),
        ('technical_error', 'Technical Error'),
        ('other', 'Other')
    ], string='Bounce Reason', tracking=True)
    
    # Enhanced status tracking
    state = fields.Selection([
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
    ], string='Status', default='draft', tracking=True)
    
    previous_state = fields.Selection([
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
    ], string='Previous Status', readonly=True, tracking=True)

    # Additional fields for enhanced tracking
    description = fields.Text('Description', tracking=True)
    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Low'),
        ('2', 'High'),
        ('3', 'Very High')
    ], string='Priority', default='0', tracking=True)
    
    company_id = fields.Many2one('res.company', string='Company', required=True, 
                                default=lambda self: self.env.user.company_id)
    company_currency_id = fields.Many2one('res.currency', related='company_id.currency_id', 
                                         string='Company Currency', readonly=True, store=True)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, 
                                 default=lambda self: self.env.company.currency_id)
    
    # Enhanced relationships
    move_line_ids = fields.One2many('account.move.line', 'cheque_id', readonly=True, 
                                   copy=False, ondelete='restrict')
    cheque_book_id = fields.Many2one('cheque.book', string='Cheque Book', tracking=True)
    category_id = fields.Many2one('cheque.category', string='Cheque Category', tracking=True)
    
    _sql_constraints = [
        ('cheque_number_uniq', 'unique(cheque_no)', 'The Cheque Number must be unique!'),
        ('sayad_number_uniq', 'unique(sayad_number)', 'The Sayad Number must be unique!'),
        ('cheque_no_company_uniq', 'unique (cheque_no,company_id)', 
         'The Cheque Number must be unique per company!'),
    ]

    @api.depends('cheque_date')
    def _compute_due_date(self):
        for record in self:
            if record.cheque_date:
                # Default due date is 30 days from cheque date
                record.due_date = record.cheque_date + timedelta(days=30)

    @api.constrains('amount')
    def _check_amount(self):
        for record in self:
            if record.amount <= 0:
                raise ValidationError(_('Cheque amount must be greater than zero.'))

    @api.onchange('payer')
    def _onchange_payer(self):
        """Automatically set the default bank account when a payer is selected."""
        if self.payer and self.payer.bank_ids:
            self.bank_account = self.payer.bank_ids[:1].id
            if self.payer.name:
                self.cheque_owner_name = self.payer.name

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

    def action_register(self):
        self.ensure_one()
        if self.state == 'draft':
            self.state = 'register'
            _logger.info(f'Cheque {self.seq_no} registered successfully')

    def action_deposit(self):
        self.ensure_one()
        if self.state == 'register':
            self.state = 'deposit'
            _logger.info(f'Cheque {self.seq_no} marked as deposited')

    def action_bounce(self):
        self.ensure_one()
        if self.state in ['deposit', 'register']:
            self.state = 'bounce'
            self.bounced = True
            _logger.info(f'Cheque {self.seq_no} marked as bounced')

    def action_return_to_cashbox(self):
        self.ensure_one()
        if self.state == 'bounce':
            self.state = 'return_cashbox'
            _logger.info(f'Cheque {self.seq_no} returned to cashbox')

    def get_cheque_status_report(self):
        self.ensure_one()
        return {
            'cheque_no': self.cheque_no,
            'amount': self.amount,
            'state': self.state,
            'days_to_due': (self.due_date - fields.Date.today()).days if self.due_date else 0,
            'is_overdue': self.due_date and self.due_date < fields.Date.today() if self.due_date else False
        }

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

class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    cheque_id = fields.Many2one('cheque.manage', 'Cheque Id')


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    cheque_id = fields.Many2one('cheque.manage', 'Cheque Id')