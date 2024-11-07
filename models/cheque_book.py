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
    
    # Enhanced tracking fields
    serial_number_start = fields.Char(string='Starting Serial Number', required=True, tracking=True)
    serial_number_end = fields.Char(string='Ending Serial Number', compute='_compute_serial_number_end', store=True)
    saad_number_start = fields.Char(string='Starting Saad Number', required=True, tracking=True)
    saad_number_current = fields.Char(string='Current Saad Number', tracking=True)
    
    bank_account = fields.Many2one('res.partner.bank', string='Bank Account', required=True, tracking=True)
    cheque_ids = fields.One2many('cheque.manage', 'cheque_book_id', string='Cheques')
    cheques_issued = fields.Integer(string='Cheques Issued', default=0, tracking=True)
    cheques_remaining = fields.Integer(string='Cheques Remaining', compute='_compute_cheques_remaining')
    
    # Status and validation
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('depleted', 'Depleted'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)
    
    active = fields.Boolean(default=True, tracking=True)
    issue_date = fields.Date(string='Issue Date', tracking=True)
    expiry_date = fields.Date(string='Expiry Date', tracking=True)
    notes = fields.Text(string='Notes', tracking=True)

    _sql_constraints = [
        ('unique_serial_start', 'UNIQUE(serial_number_start)', 'Starting Serial Number must be unique!'),
        ('unique_saad_start', 'UNIQUE(saad_number_start)', 'Starting Saad Number must be unique!')
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

    @api.constrains('serial_number_start', 'saad_number_start')
    def _check_numbers(self):
        for record in self:
            if not record.serial_number_start.isdigit():
                raise ValidationError(_('Serial number must contain only digits.'))
            if not record.saad_number_start.isdigit():
                raise ValidationError(_('Saad number must contain only digits.'))

    def action_activate(self):
        """Activate the cheque book and generate leaves."""
        self.ensure_one()
        if not self.issue_date:
            self.issue_date = fields.Date.today()
        self.state = 'active'
        self.saad_number_current = self.saad_number_start
        self._generate_cheque_leaves()
        _logger.info(f'Activated cheque book {self.name} and generated leaves')

    def action_revert_to_draft(self):
        """Revert the cheque book to draft status."""
        self.ensure_one()
        if self.cheques_issued > 0:
            raise UserError(_('Cannot revert to draft as cheques have already been issued.'))
        self.write({
            'state': 'draft',
            'cheques_issued': 0,
            'saad_number_current': False
        })
        # Delete any existing unissued leaves
        self.env['cheque.manage'].search([
            ('cheque_book_id', '=', self.id),
            ('state', '=', 'draft')
        ]).unlink()
        _logger.info(f'Reverted cheque book {self.name} to draft status')

    def _generate_cheque_leaves(self):
        """Generate cheque leaves with sequential numbers."""
        self.ensure_one()
        start_serial = int(self.serial_number_start)
        start_saad = int(self.saad_number_start)
        total_leaves = int(self.number_of_checks)

        for i in range(total_leaves):
            serial_num = str(start_serial + i).zfill(len(self.serial_number_start))
            saad_num = str(start_saad + i).zfill(len(self.saad_number_start))
            
            self.env['cheque.manage'].create({
                'cheque_book_id': self.id,
                'seq_no': serial_num,
                'sayad_number': saad_num,
                'state': 'draft',
                'bank_account': self.bank_account.id,
                'branch_code': self.branch_code,
            })
        _logger.info(f'Generated {total_leaves} cheque leaves for cheque book {self.name}')

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
        self.saad_number_current = str(int(self.saad_number_start) + self.cheques_issued - 1)
        
        if self.cheques_remaining <= 5:
            self.message_post(
                body=_('Warning: Only %s cheques remaining in this book.') % self.cheques_remaining
            )
        
        return str(next_serial_num).zfill(len(self.serial_number_start))

    def name_get(self):
        """Override name_get to include bank name and serial range."""
        result = []
        for record in self:
            name = f'{record.name} [{record.bank_name}] ({record.serial_number_start}-{record.serial_number_end})'
            result.append((record.id, name))
        return result
