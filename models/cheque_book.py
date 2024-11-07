from odoo import api, fields, models
from odoo.exceptions import UserError


class ChequeBook(models.Model):
    _name = 'cheque.book'
    _description = 'Cheque Book'

    name = fields.Char(string='Chequebook Name', required=True)
    bank_name = fields.Char(string='Bank Name', required=True)
    account_number = fields.Char(string='Account Number', required=True)
    branch_code = fields.Char(string='Branch Code')
    number_of_checks = fields.Selection(
        [('10', '10'), ('25', '25'), ('50', '50'), ('100', '100')],
        string='Number of Checks', required=True
    )
    bank_account = fields.Many2one('res.partner.bank', string='Bank Account', required=True)
    serial_number_start = fields.Char(string='Starting Serial Number', required=True)
    serial_number_end = fields.Char(string='Ending Serial Number', compute='_compute_serial_number_end', store=True)
    cheque_ids = fields.One2many('cheque.manage', 'cheque_book_id', string='Cheques')
    cheques_issued = fields.Integer(string='Cheques Issued', default=0)

    @api.depends('serial_number_start', 'number_of_checks')
    def _compute_serial_number_end(self):
        for record in self:
            if record.serial_number_start:
                start = int(record.serial_number_start)
                end = start + int(record.number_of_checks) - 1
                record.serial_number_end = str(end).zfill(16)

    def get_next_serial_number(self):
        serial_start_num = int(self.serial_number_start)
        next_serial_num = serial_start_num + self.cheques_issued

        serial_end_num = int(self.serial_number_end)
        if next_serial_num > serial_end_num:
            raise UserError('All checks in this cheque book have been used.')

        self.cheques_issued += 1
        return str(next_serial_num).zfill(16)
