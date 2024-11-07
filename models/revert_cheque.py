from datetime import timedelta
from odoo import api, fields, models
import logging


_logger = logging.getLogger(__name__)

class RevertCheque(models.Model):
    _name = 'revert.cheque'
    _description = 'Revert Cheque'

    original_cheque_id = fields.Integer(string='Original Cheque ID')
    seq_no = fields.Char(string='Sequence')
    name = fields.Char(string='Name')
    attachment_count = fields.Integer(string='Attachment Count')
    journal_item_count = fields.Integer(string='Journal Items')
    payer = fields.Many2one('res.partner', 'Payee')
    bank_account = fields.Many2one('account.account', string='Bank Account')
    debit_account = fields.Many2one('account.account', string='Debit Account')
    credit_account = fields.Many2one('account.account', string='Credit Account')
    debit = fields.Monetary(default=0.0, currency_field='company_currency_id')
    credit = fields.Monetary(default=0.0, currency_field='company_currency_id')
    journal_id = fields.Many2one('account.journal', string='Journal')
    cheque_date = fields.Date(string='Cheque Date')
    cashed_date = fields.Date(string='Cashed Date')
    return_date = fields.Date(string='Returned Date')
    cheque_receive_date = fields.Date(string='Cheque Given/Receive Date')
    cheque_no = fields.Char(string='Cheque Number')
    amount = fields.Float(string='Amount')
    bounced = fields.Boolean(string='Bounced')
    partner_id = fields.Many2one('res.partner', 'Company')
    cheq_type = fields.Selection([('incoming', 'Incoming'), ('outgoing', 'Outgoing')])
    cheq_attachment_ids = fields.One2many('ir.attachment', 'cheque_id', string='Attachment Line')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('register', 'Registered'),
        ('deposit', 'Deposited'),
        ('done', 'Done'),
        ('transfer', 'Transferred'),
        ('bounce', 'Bounced'),
        ('return', 'Returned'),
        ('cancel', 'Cancelled'),
    ], string='Status')
    description = fields.Text('Description')
    company_id = fields.Many2one('res.company', string='Company')
    company_currency_id = fields.Many2one('res.currency', string='Company Currency')
    move_line_ids = fields.One2many('account.move.line', 'cheque_id', string='Related Journal Items')
    deletion_date = fields.Datetime(string='Deletion Date',
                                    default=fields.Datetime.now)

    @api.model
    def delete_old_archives(self):
        one_week_ago = fields.Datetime.now() - timedelta(days=7)
        old_archives = self.search([('deletion_date', '<', one_week_ago)])
        old_archives.unlink()
        _logger.info(f"Successfully deleted {len(old_archives)} old archive(s) older than one week.")

    def restore_cheque(self):
        cheque_manage_model = self.env['cheque.manage']
        restored_cheques = []

        for archived_cheque in self:
            restored_cheque = cheque_manage_model.create({
                'seq_no': archived_cheque.seq_no,
                'name': archived_cheque.name,
                'payer': archived_cheque.payer.id,
                'bank_account': archived_cheque.bank_account.id,
                'debit_account': archived_cheque.debit_account.id,
                'credit_account': archived_cheque.credit_account.id,
                'debit': archived_cheque.debit,
                'credit': archived_cheque.credit,
                'journal_id': archived_cheque.journal_id.id,
                'cheque_date': archived_cheque.cheque_date,
                'cashed_date': archived_cheque.cashed_date,
                'return_date': archived_cheque.return_date,
                'cheque_receive_date': archived_cheque.cheque_receive_date,
                'cheque_no': archived_cheque.cheque_no,
                'amount': archived_cheque.amount,
                'bounced': archived_cheque.bounced,
                'partner_id': archived_cheque.partner_id.id,
                'cheq_type': archived_cheque.cheq_type,
                'state': 'draft',
                'description': archived_cheque.description,
                'company_id': archived_cheque.company_id.id,
                'company_currency_id': archived_cheque.company_currency_id.id,
                'move_line_ids': [(6, 0, archived_cheque.move_line_ids.ids)],
            })
            _logger.info(f"Cheque restored with new ID: {restored_cheque.id}")
            restored_cheques.append(restored_cheque)
            for move in restored_cheque.move_line_ids.mapped('move_id'):
                if move.state == 'draft':
                    _logger.info(
                        f"Posting journal entry with ID: {move.id} for restored cheque ID: {restored_cheque.id}")
                    move.action_post()
        self.unlink()
        _logger.info(f"Archived cheques with IDs: {self.ids} deleted after restoration")
        return {
            'type': 'ir.actions.act_window',
            'name': 'Restored Cheque',
            'res_model': 'cheque.manage',
            'view_mode': 'form',
            'res_id': restored_cheques[0].id if restored_cheques else False,
            'target': 'current',
        }
