from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
import logging
import re

_logger = logging.getLogger(__name__)

class PaymentProcessor(models.Model):
    _name = 'payment.processor'
    _description = 'Payment Processor'
    _inherit = ['mail.thread']

    name = fields.Char(string='Processor Name', required=True, tracking=True)
    code = fields.Char(string='Processor Code', required=True, tracking=True)
    payment_method = fields.Selection([
        ('bank_transfer', 'Bank Transfer'),
        ('credit_card', 'Credit Card'),
        ('debit_card', 'Debit Card'),
        ('digital_wallet', 'Digital Wallet'),
        ('cash', 'Cash'),
        ('cheque', 'Cheque')
    ], string='Payment Method', required=True, tracking=True)
    
    # Processing configuration
    api_endpoint = fields.Char(string='API Endpoint')
    api_key = fields.Char(string='API Key')
    merchant_id = fields.Char(string='Merchant ID')
    
    # Enhanced security settings
    encryption_enabled = fields.Boolean(string='Enable Encryption', default=True)
    require_2fa = fields.Boolean(string='Require 2FA', default=False)
    max_daily_limit = fields.Float(string='Maximum Daily Limit')
    max_transaction_limit = fields.Float(string='Maximum Transaction Limit')
    
    # Account settings
    journal_id = fields.Many2one('account.journal', string='Payment Journal', required=True)
    debit_account_id = fields.Many2one('account.account', string='Debit Account')
    credit_account_id = fields.Many2one('account.account', string='Credit Account')
    
    # Status and validation
    active = fields.Boolean(default=True, tracking=True)
    test_mode = fields.Boolean(string='Test Mode', default=True, tracking=True)
    
    # Processing fees
    fee_type = fields.Selection([
        ('fixed', 'Fixed'),
        ('percentage', 'Percentage'),
        ('mixed', 'Mixed')
    ], string='Fee Type', default='fixed')
    fixed_fee = fields.Float(string='Fixed Fee Amount')
    percentage_fee = fields.Float(string='Percentage Fee')
    
    # Audit fields
    last_transaction_date = fields.Datetime(string='Last Transaction Date', readonly=True)
    total_transactions = fields.Integer(string='Total Transactions', readonly=True)
    total_amount_processed = fields.Float(string='Total Amount Processed', readonly=True)
    
    _sql_constraints = [
        ('unique_code', 'unique(code)', 'Processor code must be unique!')
    ]

    @api.constrains('api_endpoint')
    def _check_api_endpoint(self):
        for record in self:
            if record.api_endpoint and not re.match(r'^https?:\/\/.+', record.api_endpoint):
                raise ValidationError(_('API Endpoint must start with http:// or https://'))

    def calculate_processing_fee(self, amount):
        """Calculate processing fee based on fee type"""
        self.ensure_one()
        if self.fee_type == 'fixed':
            return self.fixed_fee
        elif self.fee_type == 'percentage':
            return amount * (self.percentage_fee / 100)
        else:  # mixed
            return self.fixed_fee + (amount * (self.percentage_fee / 100))

    def _check_transaction_limits(self, amount):
        """Check if transaction amount is within limits"""
        self.ensure_one()
        if self.max_transaction_limit and amount > self.max_transaction_limit:
            raise ValidationError(_('Transaction amount exceeds the maximum limit.'))
        
        if self.max_daily_limit:
            today_total = self.env['account.payment'].search([
                ('payment_processor_id', '=', self.id),
                ('payment_date', '=', fields.Date.today()),
                ('state', 'in', ['posted', 'reconciled'])
            ]).mapped('amount')
            if sum(today_total) + amount > self.max_daily_limit:
                raise ValidationError(_('This transaction would exceed the daily processing limit.'))

    def process_payment(self, payment):
        """Process payment using the configured payment method"""
        self.ensure_one()
        
        if not self.active:
            raise UserError(_('This payment processor is not active.'))
            
        if payment.amount <= 0:
            raise ValidationError(_('Payment amount must be greater than zero.'))
            
        # Check transaction limits
        self._check_transaction_limits(payment.amount)
        
        try:
            # Calculate processing fee
            processing_fee = self.calculate_processing_fee(payment.amount)
            
            # Create journal entries for payment and fee
            move_vals = {
                'date': fields.Date.today(),
                'journal_id': self.journal_id.id,
                'ref': f'Payment: {payment.name}',
                'line_ids': [
                    (0, 0, {
                        'account_id': self.debit_account_id.id,
                        'debit': payment.amount,
                        'credit': 0.0,
                        'name': f'Payment received via {self.name}',
                    }),
                    (0, 0, {
                        'account_id': self.credit_account_id.id,
                        'debit': 0.0,
                        'credit': payment.amount - processing_fee,
                        'name': f'Payment processed via {self.name}',
                    })
                ]
            }
            
            # Add processing fee entry if applicable
            if processing_fee > 0:
                move_vals['line_ids'].append((0, 0, {
                    'account_id': self.journal_id.default_account_id.id,
                    'debit': 0.0,
                    'credit': processing_fee,
                    'name': f'Processing fee for {self.name}',
                }))
            
            move = self.env['account.move'].create(move_vals)
            move.action_post()
            
            # Update audit fields
            self.write({
                'last_transaction_date': fields.Datetime.now(),
                'total_transactions': self.total_transactions + 1,
                'total_amount_processed': self.total_amount_processed + payment.amount
            })
            
            _logger.info(f'Payment processed successfully via {self.name}')
            return True
            
        except Exception as e:
            _logger.error(f'Payment processing failed: {str(e)}')
            raise UserError(_('Payment processing failed: %s') % str(e))
