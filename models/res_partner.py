from datetime import timedelta
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    weighted_avg_due_date = fields.Date(string='Weighted Average Due Date', readonly=True)

    def calculate_weighted_average_due_date(self):
        for partner in self:
            cheques = self.env['cheque.manage'].search([('payer', '=', partner.id), ('state', '=', 'register')])
            total_amount = sum(cheque.amount for cheque in cheques)

            if not total_amount:
                partner.weighted_avg_due_date = False
                continue

            weighted_days = sum(
                (cheque.cheque_date - fields.Date.today()).days * cheque.amount
                for cheque in cheques
            )
            average_days = round(weighted_days / total_amount)
            partner.weighted_avg_due_date = fields.Date.today() + timedelta(days=average_days)
