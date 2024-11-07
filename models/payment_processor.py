from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
import logging
import re
import json
import hashlib
from datetime import datetime, timedelta

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
    
    # Enhanced digital wallet support
    digital_wallet_type = fields.Selection([
        ('paypal', 'PayPal'),
        ('stripe', 'Stripe'),
        ('apple_pay', 'Apple Pay'),
        ('google_pay', 'Google Pay'),
        ('other', 'Other')
    ], string='Digital Wallet Type')
    wallet_config = fields.Text(string='Wallet Configuration', help='JSON configuration for digital wallet')
    
    # Enhanced processing configuration
    api_endpoint = fields.Char(string='API Endpoint')
    api_key = fields.Char(string='API Key')
    merchant_id = fields.Char(string='Merchant ID')
    webhook_url = fields.Char(string='Webhook URL')
    
    # Enhanced security settings
    encryption_enabled = fields.Boolean(string='Enable Encryption', default=True)
    encryption_method = fields.Selection([
        ('aes256', 'AES-256'),
        ('rsa', 'RSA'),
        ('tls', 'TLS 1.3')
    ], string='Encryption Method', default='aes256')
    require_2fa = fields.Boolean(string='Require 2FA', default=False)
    max_daily_limit = fields.Float(string='Maximum Daily Limit')
    max_transaction_limit = fields.Float(string='Maximum Transaction Limit')
    failed_attempt_limit = fields.Integer(string='Failed Attempt Limit', default=3)
    lockout_duration = fields.Integer(string='Lockout Duration (minutes)', default=30)
    
    # Enhanced account settings
    journal_id = fields.Many2one('account.journal', string='Payment Journal', required=True)
    debit_account_id = fields.Many2one('account.account', string='Debit Account')
    credit_account_id = fields.Many2one('account.account', string='Credit Account')
    fee_account_id = fields.Many2one('account.account', string='Fee Account')
    
    # Enhanced status and validation
    active = fields.Boolean(default=True, tracking=True)
    test_mode = fields.Boolean(string='Test Mode', default=True, tracking=True)
    status = fields.Selection([
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('locked', 'Locked'),
        ('maintenance', 'Maintenance')
    ], string='Status', default='active', tracking=True)
    last_status_check = fields.Datetime(string='Last Status Check')
    
    # Enhanced processing fees
    fee_type = fields.Selection([
        ('fixed', 'Fixed'),
        ('percentage', 'Percentage'),
        ('mixed', 'Mixed'),
        ('tiered', 'Tiered'),
        ('dynamic', 'Dynamic')
    ], string='Fee Type', default='fixed')
    fixed_fee = fields.Float(string='Fixed Fee Amount')
    percentage_fee = fields.Float(string='Percentage Fee')
    fee_tiers = fields.Text(string='Fee Tiers', help='JSON configuration for tiered fees')
    minimum_fee = fields.Float(string='Minimum Fee')
    maximum_fee = fields.Float(string='Maximum Fee')
    
    # Enhanced audit fields
    last_transaction_date = fields.Datetime(string='Last Transaction Date', readonly=True)
    total_transactions = fields.Integer(string='Total Transactions', readonly=True)
    total_amount_processed = fields.Float(string='Total Amount Processed', readonly=True)
    failed_transactions = fields.Integer(string='Failed Transactions', readonly=True)
    average_processing_time = fields.Float(string='Average Processing Time (s)', readonly=True)
    
    _sql_constraints = [
        ('unique_code', 'unique(code)', 'Processor code must be unique!')
    ]

    @api.constrains('api_endpoint')
    def _check_api_endpoint(self):
        for record in self:
            if record.api_endpoint and not re.match(r'^https?:\/\/.+', record.api_endpoint):
                raise ValidationError(_('API Endpoint must start with http:// or https://'))

    @api.constrains('fee_type', 'fixed_fee', 'percentage_fee', 'fee_tiers')
    def _check_fees(self):
        for record in self:
            if record.fee_type == 'fixed' and record.fixed_fee <= 0:
                raise ValidationError(_('Fixed fee must be greater than zero.'))
            elif record.fee_type == 'percentage' and (record.percentage_fee <= 0 or record.percentage_fee > 100):
                raise ValidationError(_('Percentage fee must be between 0 and 100.'))
            elif record.fee_type == 'mixed' and (record.fixed_fee <= 0 or record.percentage_fee <= 0):
                raise ValidationError(_('Both fixed and percentage fees must be greater than zero for mixed fee type.'))
            elif record.fee_type == 'tiered' and not record.fee_tiers:
                raise ValidationError(_('Fee tiers configuration is required for tiered fee type.'))

    @api.onchange('payment_method')
    def _onchange_payment_method(self):
        if self.payment_method == 'digital_wallet' and not self.digital_wallet_type:
            return {
                'warning': {
                    'title': _('Configuration Required'),
                    'message': _('Please select a digital wallet type and configure the wallet settings.')
                }
            }

    def calculate_processing_fee(self, amount):
        """Calculate processing fee based on fee type with enhanced logic"""
        self.ensure_one()
        calculated_fee = 0.0

        if self.fee_type == 'fixed':
            calculated_fee = self.fixed_fee
        elif self.fee_type == 'percentage':
            calculated_fee = amount * (self.percentage_fee / 100)
        elif self.fee_type == 'mixed':
            calculated_fee = self.fixed_fee + (amount * (self.percentage_fee / 100))
        elif self.fee_type == 'tiered':
            if self.fee_tiers:
                tiers = json.loads(self.fee_tiers)
                for tier in sorted(tiers, key=lambda x: x['max_amount']):
                    if amount <= tier['max_amount']:
                        calculated_fee = tier['fixed_fee'] + (amount * tier['percentage'] / 100)
                        break
        elif self.fee_type == 'dynamic':
            # Dynamic fee calculation based on transaction volume and time
            daily_volume = self._get_daily_transaction_volume()
            calculated_fee = self._calculate_dynamic_fee(amount, daily_volume)

        # Apply minimum and maximum fee constraints
        if self.minimum_fee and calculated_fee < self.minimum_fee:
            calculated_fee = self.minimum_fee
        if self.maximum_fee and calculated_fee > self.maximum_fee:
            calculated_fee = self.maximum_fee

        return calculated_fee

    def _calculate_dynamic_fee(self, amount, daily_volume):
        """Calculate dynamic fee based on transaction volume and time of day"""
        base_fee = amount * (self.percentage_fee / 100)
        
        # Volume discount
        if daily_volume > 1000000:
            base_fee *= 0.8  # 20% discount for high volume
        elif daily_volume > 500000:
            base_fee *= 0.9  # 10% discount for medium volume
            
        # Time-based adjustment
        current_hour = datetime.now().hour
        if 0 <= current_hour < 6:  # Off-peak hours
            base_fee *= 0.95
            
        return base_fee

    def _get_daily_transaction_volume(self):
        """Get total transaction volume for the current day"""
        today_start = fields.Datetime.now().replace(hour=0, minute=0, second=0)
        today_transactions = self.env['account.payment'].search([
            ('payment_processor_id', '=', self.id),
            ('payment_date', '>=', today_start),
            ('state', 'in', ['posted', 'reconciled'])
        ])
        return sum(today_transactions.mapped('amount'))

    def _check_transaction_limits(self, amount):
        """Enhanced transaction limit checks"""
        self.ensure_one()
        
        # Check transaction amount limit
        if self.max_transaction_limit and amount > self.max_transaction_limit:
            raise ValidationError(_('Transaction amount exceeds the maximum limit of %s.') % 
                                self.max_transaction_limit)
            
        # Check daily limit
        if self.max_daily_limit:
            daily_total = self._get_daily_transaction_volume()
            if daily_total + amount > self.max_daily_limit:
                raise ValidationError(_('This transaction would exceed the daily processing limit of %s.') % 
                                    self.max_daily_limit)

        # Check for suspicious activity
        if self._detect_suspicious_activity(amount):
            self._handle_suspicious_activity()

    def _detect_suspicious_activity(self, amount):
        """Detect suspicious transaction patterns"""
        recent_transactions = self.env['account.payment'].search([
            ('payment_processor_id', '=', self.id),
            ('create_date', '>=', fields.Datetime.now() - timedelta(hours=1))
        ])
        
        # Check for unusual frequency
        if len(recent_transactions) > 10:  # More than 10 transactions per hour
            return True
            
        # Check for unusual amount patterns
        avg_amount = sum(recent_transactions.mapped('amount')) / len(recent_transactions) if recent_transactions else 0
        if amount > (avg_amount * 5):  # Amount is 5 times larger than average
            return True
            
        return False

    def _handle_suspicious_activity(self):
        """Handle detected suspicious activity"""
        self.status = 'locked'
        self.message_post(
            body=_('Processor locked due to suspicious activity. Manual review required.'),
            message_type='notification'
        )
        raise UserError(_('Transaction blocked due to suspicious activity. Please contact support.'))

    def process_payment(self, payment):
        """Process payment with enhanced security and validation"""
        self.ensure_one()
        
        if not self.active or self.status != 'active':
            raise UserError(_('This payment processor is currently not available.'))
            
        if payment.amount <= 0:
            raise ValidationError(_('Payment amount must be greater than zero.'))
            
        # Enhanced validation checks
        self._check_transaction_limits(payment.amount)
        if self.require_2fa and not self._verify_2fa(payment):
            raise ValidationError(_('Two-factor authentication required.'))
            
        start_time = datetime.now()
        try:
            # Calculate processing fee
            processing_fee = self.calculate_processing_fee(payment.amount)
            
            # Create journal entries for payment and fee
            move_vals = self._prepare_payment_move(payment, processing_fee)
            move = self.env['account.move'].create(move_vals)
            move.action_post()
            
            # Update audit fields
            processing_time = (datetime.now() - start_time).total_seconds()
            self._update_processor_statistics(payment.amount, processing_time)
            
            # Process digital wallet specific logic
            if self.payment_method == 'digital_wallet':
                self._process_digital_wallet_payment(payment)
            
            _logger.info(f'Payment processed successfully via {self.name}')
            return True
            
        except Exception as e:
            self.failed_transactions += 1
            _logger.error(f'Payment processing failed: {str(e)}')
            raise UserError(_('Payment processing failed: %s') % str(e))

    def _prepare_payment_move(self, payment, processing_fee):
        """Prepare move values for payment and processing fee"""
        move_lines = [
            (0, 0, {
                'account_id': self.debit_account_id.id,
                'debit': payment.amount,
                'credit': 0.0,
                'name': f'Payment received via {self.name}',
                'partner_id': payment.partner_id.id,
            }),
            (0, 0, {
                'account_id': self.credit_account_id.id,
                'debit': 0.0,
                'credit': payment.amount - processing_fee,
                'name': f'Payment processed via {self.name}',
                'partner_id': payment.partner_id.id,
            })
        ]
        
        if processing_fee > 0:
            move_lines.append((0, 0, {
                'account_id': self.fee_account_id.id,
                'debit': 0.0,
                'credit': processing_fee,
                'name': f'Processing fee for {self.name}',
                'partner_id': payment.partner_id.id,
            }))
            
        return {
            'date': fields.Date.today(),
            'journal_id': self.journal_id.id,
            'ref': f'Payment: {payment.name}',
            'line_ids': move_lines
        }

    def _update_processor_statistics(self, amount, processing_time):
        """Update processor statistics after successful payment"""
        self.write({
            'last_transaction_date': fields.Datetime.now(),
            'total_transactions': self.total_transactions + 1,
            'total_amount_processed': self.total_amount_processed + amount,
            'average_processing_time': (
                (self.average_processing_time * self.total_transactions + processing_time) /
                (self.total_transactions + 1)
            )
        })

    def _process_digital_wallet_payment(self, payment):
        """Process digital wallet specific payment logic"""
        if not self.digital_wallet_type:
            raise ValidationError(_('Digital wallet type not configured.'))
            
        try:
            wallet_config = json.loads(self.wallet_config or '{}')
            if self.digital_wallet_type == 'paypal':
                self._process_paypal_payment(payment, wallet_config)
            elif self.digital_wallet_type == 'stripe':
                self._process_stripe_payment(payment, wallet_config)
            # Add other wallet types as needed
        except json.JSONDecodeError:
            raise ValidationError(_('Invalid wallet configuration.'))

    def _verify_2fa(self, payment):
        """Verify two-factor authentication"""
        # Implementation depends on the 2FA method used
        return True  # Placeholder for actual 2FA implementation

    def check_processor_status(self):
        """Check and update processor status"""
        self.ensure_one()
        self.last_status_check = fields.Datetime.now()
        
        if self.failed_transactions > self.failed_attempt_limit:
            self.status = 'locked'
            return False
            
        # Add additional status checks as needed
        return True

    def generate_security_hash(self, payment_data):
        """Generate security hash for payment verification"""
        hash_string = f"{payment_data['amount']}{payment_data['currency']}{payment_data['timestamp']}{self.api_key}"
        return hashlib.sha256(hash_string.encode()).hexdigest()
