# -*- coding: utf-8 -*-
##############################################################################
#
#    Globalteckz Pvt Ltd
#    Copyright (C) 2013-Today(www.globalteckz.com).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
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
{
    'name': 'Enhanced Cheque/Check Management in Odoo',
    'version': '17.0.2.0.0',
    'author': 'Globalteckz',
    'category': 'Accounting',
    'description': """
Comprehensive financial transaction management system with advanced features:
- Multi-branch operations with hierarchical management
- Enhanced payment processing with multiple payment methods
- Advanced cash flow analysis and forecasting
- Comprehensive reporting system
- Enhanced security and validation
""",
    'website': 'https://www.globalteckz.com',
    'summary': """Complete financial transaction management with multi-branch support, advanced analytics, and enhanced security.""",
    'depends': [
        'base',
        'account',
        'attachment_indexation',
        'account_accountant',
        'sms',
        'whatsapp',
        'mail',
        'web',
        'base_automation',
        'portal',
    ],
    'external_dependencies': {
        'python': [
            'pandas',
            'numpy',
            'plotly',
            'streamlit',
            'scipy'
        ],
    },
    "license": 'Other proprietary',
    'images': ['static/description/Banner.gif'],
    "price": "49.00",
    "currency": "EUR",
    'data': [
        'security/branch_security.xml',
        'security/ir.model.access.csv',
        'wizard/cheque_wizard.xml',
        'wizard/batch_assign_to_supplier_wizard.xml',
        'wizard/report_wizard_view.xml',
        'report/report_wizard_view.xml',
        'report/cheque_report.xml',
        'report/advanced_report_template.xml',
        'views/branch_view.xml',
        'views/payment_processor_view.xml',
        'views/cheque_payment.xml',
        'views/cheque_spend.xml',
        'views/cheque_book.xml',
        'views/ir_sequence_data.xml',
        'views/cheque_manage.xml',
        'views/res_config.xml',
        'views/account_accountant.xml',
        'views/revert_cheque.xml',
        'views/res_partner.xml',
        'views/cheque_category.xml',
        'data/cron_cheque_notifications.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'gt_cheque_management/static/src/js/*.js',
            'gt_cheque_management/static/src/css/*.css',
        ],
    },
    'qweb': [],
    'test': [],
    'installable': True,
    'auto_install': False,
    'application': True,
}
