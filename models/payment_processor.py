from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
import logging

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
    
    _sql_constraints = [
        ('unique_code', 'unique(code)', 'Processor code must be unique!')
    ]

    @api.constrains('fee_type', 'fixed_fee', 'percentage_fee')
    def _check_fees(self):
        for record in self:
            if record.fee_type == 'fixed' and record.fixed_fee <= 0:
                raise ValidationError(_('Fixed fee must be greater than zero.'))
            elif record.fee_type == 'percentage' and (record.percentage_fee <= 0 or record.percentage_fee > 100):
                raise ValidationError(_('Percentage fee must be between 0 and 100.'))
            elif record.fee_type == 'mixed' and (record.fixed_fee <= 0 or record.percentage_fee <= 0):
                raise ValidationError(_('Both fixed and percentage fees must be greater than zero for mixed fee type.'))

    def calculate_processing_fee(self, amount):
        self.ensure_one()
        if self.fee_type == 'fixed':
            return self.fixed_fee
        elif self.fee_type == 'percentage':
            return amount * (self.percentage_fee / 100)
        else:  # mixed
            return self.fixed_fee + (amount * (self.percentage_fee / 100))

    def process_payment(self, payment):
        """Process payment using the configured payment method"""
        self.ensure_one()
        
        if not self.active:
            raise UserError(_('This payment processor is not active.'))
            
        if payment.amount <= 0:
            raise ValidationError(_('Payment amount must be greater than zero.'))
            
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
        
        _logger.info(f'Payment processed successfully via {self.name}')
        return True
