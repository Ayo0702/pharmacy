from odoo import models, fields, api

class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    is_hmo = fields.Boolean(string='Is HMO Payment', default=False)
    payment_category = fields.Selection([
        ('cash', 'Cash'),
        ('online', 'Online/Bank'),
        ('hmo', 'HMO Receivable')
    ], string='Payment Category', default='cash')
    hmo_receivable_account_id = fields.Many2one(
        'account.account', string='HMO Receivable Account',
        domain="[('account_type', '=', 'asset_receivable'), ('deprecated', '=', False)]"
    )
