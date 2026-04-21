from odoo import models, fields, api, tools

class BigFixReportPayments(models.Model):
    _name = 'bigfix.pharmacy.payment.report'
    _description = 'Pharmacy Payment Analysis'
    _auto = False

    branch_id = fields.Many2one('res.branch', string='Branch', readonly=True)
    payment_category = fields.Selection([
        ('cash', 'Cash'),
        ('online', 'Online/Bank'),
        ('hmo', 'HMO Receivable')
    ], string='Payment Category', readonly=True)
    amount = fields.Float(string='Total Amount', readonly=True)
    date = fields.Date(string='Date', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    ROW_NUMBER() OVER() as id,
                    po.branch_id,
                    ppm.payment_category,
                    sum(pp.amount) as amount,
                    pp.payment_date::date as date
                FROM pos_payment pp
                JOIN pos_order po ON pp.pos_order_id = po.id
                JOIN pos_payment_method ppm ON pp.payment_method_id = ppm.id
                WHERE po.state IN ('paid', 'done', 'invoiced')
                GROUP BY po.branch_id, ppm.payment_category, pp.payment_date::date
            )
        """ % self._table)
