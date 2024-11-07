from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)

class ChequeBook(models.Model):
    _name = 'cheque.book'
    _description = 'Cheque Book'
    _inherit = ['mail.thread']

    name = fields.Char(string='Chequebook Name', required=True, tracking=True)
    bank_name = fields.Char(string='Bank Name', required=True, tracking=True)
    account_number = fields.Char(string='Account Number', required=True, tracking=True)
    branch_code = fields.Char(string='Branch Code', tracking=True)
    number_of_checks = fields.Selection([
        ('10', '10'), ('25', '25'), ('50', '50'), ('100', '100')
    ], string='Number of Checks', required=True, tracking=True)
    
    bank_account = fields.Many2one('res.partner.bank', string='Bank Account', required=True, tracking=True)
    serial_number_start = fields.Char(string='Starting Serial Number', required=True, tracking=True)
    serial_number_end = fields.Char(string='Ending Serial Number', compute='_compute_serial_number_end', store=True)
    
    # Enhanced tracking fields
    cheque_ids = fields.One2many('cheque.manage', 'cheque_book_id', string='Cheques')
    cheques_issued = fields.Integer(string='Cheques Issued', default=0, tracking=True)
    cheques_remaining = fields.Integer(string='Cheques Remaining', compute='_compute_cheques_remaining')
    active = fields.Boolean(default=True, tracking=True)
    
    # Status tracking
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('depleted', 'Depleted'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)
    
    # Additional information
    issue_date = fields.Date(string='Issue Date', tracking=True)
    expiry_date = fields.Date(string='Expiry Date', tracking=True)
    notes = fields.Text(string='Notes', tracking=True)
    
    _sql_constraints = [
        ('unique_serial_start', 'UNIQUE(serial_number_start)', 'Starting Serial Number must be unique!'),
        ('unique_serial_end', 'UNIQUE(serial_number_end)', 'Ending Serial Number must be unique!')
    ]

    @api.depends('serial_number_start', 'number_of_checks')
    def _compute_serial_number_end(self):
        for record in self:
            if record.serial_number_start:
                try:
                    start = int(record.serial_number_start)
                    end = start + int(record.number_of_checks) - 1
                    record.serial_number_end = str(end).zfill(len(record.serial_number_start))
                except ValueError:
                    raise ValidationError(_('Serial number must be numeric.'))

    @api.depends('number_of_checks', 'cheques_issued')
    def _compute_cheques_remaining(self):
        for record in self:
            total = int(record.number_of_checks) if record.number_of_checks else 0
            record.cheques_remaining = total - record.cheques_issued
            if record.cheques_remaining <= 0 and record.state == 'active':
                record.state = 'depleted'

    @api.constrains('serial_number_start')
    def _check_serial_number(self):
        for record in self:
            if not record.serial_number_start.isdigit():
                raise ValidationError(_('Serial number must contain only digits.'))

    def get_next_serial_number(self):
        """Get the next available serial number from the cheque book."""
        self.ensure_one()
        if self.state != 'active':
            raise UserError(_('Cannot issue cheques from an inactive cheque book.'))

        if self.cheques_remaining <= 0:
            raise UserError(_('All cheques in this book have been used.'))

        serial_start_num = int(self.serial_number_start)
        next_serial_num = serial_start_num + self.cheques_issued
        
        self.cheques_issued += 1
        _logger.info(f'Issued cheque number {next_serial_num} from cheque book {self.name}')
        
        if self.cheques_remaining <= 5:
            self.message_post(
                body=_('Warning: Only %s cheques remaining in this book.') % self.cheques_remaining
            )
        
        return str(next_serial_num).zfill(len(self.serial_number_start))

    def action_activate(self):
        """Activate the cheque book for use."""
        self.ensure_one()
        if not self.issue_date:
            self.issue_date = fields.Date.today()
        self.state = 'active'
        _logger.info(f'Activated cheque book {self.name}')

    def action_cancel(self):
        """Cancel the cheque book."""
        self.ensure_one()
        if self.cheques_issued > 0:
            raise UserError(_('Cannot cancel a cheque book that has issued cheques.'))
        self.state = 'cancelled'
        _logger.info(f'Cancelled cheque book {self.name}')

    def name_get(self):
        """Override name_get to include bank name and serial range."""
        result = []
        for record in self:
            name = f'{record.name} [{record.bank_name}] ({record.serial_number_start}-{record.serial_number_end})'
            result.append((record.id, name))
        return result
