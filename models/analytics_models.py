from odoo import models, fields, api, tools

class BigFixReportSales(models.Model):
    _name = 'bigfix.report.sales'
    _description = 'Pharmacy Sales Analysis'
    _auto = False
    _rec_name = 'date_order'

    branch_id = fields.Many2one('res.branch', string='Branch', readonly=True)
    date_order = fields.Date(string='Order Date', readonly=True)
    total_orders = fields.Integer(string='Total Orders', readonly=True)
    total_sales = fields.Float(string='Total Sales', readonly=True)
    avg_order_value = fields.Float(string='Avg Order Value', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    ROW_NUMBER() OVER() as id,
                    branch_id,
                    date_order::date as date_order,
                    count(id) as total_orders,
                    sum(amount_total) as total_sales,
                    CASE WHEN count(id) > 0 THEN sum(amount_total) / count(id) ELSE 0 END as avg_order_value
                FROM pos_order
                WHERE state IN ('paid', 'done', 'invoiced')
                GROUP BY branch_id, date_order::date
            )
        """ % self._table)


class BigFixReportProductLocation(models.Model):
    _name = 'bigfix.report.product.location'
    _description = 'Product Sales by Location'
    _auto = False

    branch_id = fields.Many2one('res.branch', string='Branch', readonly=True)
    location_id = fields.Many2one('stock.location', string='Location', readonly=True)
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    qty_sold = fields.Float(string='Quantity Sold', readonly=True)
    revenue = fields.Float(string='Revenue', readonly=True)
    period_start = fields.Date(string='Month', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    ROW_NUMBER() OVER() as id,
                    po.branch_id,
                    spt.default_location_src_id as location_id,
                    pol.product_id,
                    sum(pol.qty) as qty_sold,
                    sum(pol.price_subtotal_incl) as revenue,
                    date_trunc('month', po.date_order)::date as period_start
                FROM pos_order_line pol
                JOIN pos_order po ON pol.order_id = po.id
                JOIN pos_session ps ON po.session_id = ps.id
                JOIN pos_config pc ON ps.config_id = pc.id
                JOIN stock_picking_type spt ON pc.picking_type_id = spt.id
                WHERE po.state IN ('paid', 'done', 'invoiced')
                GROUP BY po.branch_id, spt.default_location_src_id, pol.product_id, date_trunc('month', po.date_order)
            )
        """ % self._table)


class BigFixReportStockSale(models.Model):
    _name = 'bigfix.report.stock.sale'
    _description = 'Stock Coverage Analysis'
    _auto = False

    branch_id = fields.Many2one('res.branch', string='Branch', readonly=True)
    location_id = fields.Many2one('stock.location', string='Location', readonly=True)
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    current_stock = fields.Float(string='Current Stock', readonly=True)
    avg_daily_sales = fields.Float(string='Avg Daily Sales (30d)', readonly=True)
    days_of_coverage = fields.Float(string='Days of Coverage', readonly=True)
    stock_status = fields.Selection([
        ('critical', 'Critical (< 7 days)'),
        ('warning', 'Warning (7-14 days)'),
        ('healthy', 'Healthy (> 14 days)')
    ], string='Stock Status', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                WITH monthly_sales AS (
                    SELECT 
                        po.branch_id,
                        pol.product_id,
                        sum(pol.qty) / 30.0 as avg_daily_sales
                    FROM pos_order_line pol
                    JOIN pos_order po ON pol.order_id = po.id
                    WHERE po.date_order >= now() - interval '30 days'
                    AND po.state IN ('paid', 'done', 'invoiced')
                    GROUP BY po.branch_id, pol.product_id
                ),
                current_stock AS (
                    SELECT 
                        sq.product_id,
                        sq.location_id,
                        sum(sq.quantity) as quantity
                    FROM stock_quant sq
                    JOIN stock_location sl ON sq.location_id = sl.id
                    JOIN stock_location wsl ON sl.parent_path LIKE wsl.parent_path || '%%'
                    JOIN stock_warehouse sw ON sw.view_location_id = wsl.id
                    WHERE sl.usage = 'internal'
                    GROUP BY sq.product_id, sq.location_id
                )
                SELECT
                    ROW_NUMBER() OVER() as id,
                    rb.id as branch_id,
                    cs.location_id,
                    ms.product_id,
                    coalesce(cs.quantity, 0) as current_stock,
                    coalesce(ms.avg_daily_sales, 0) as avg_daily_sales,
                    CASE 
                        WHEN ms.avg_daily_sales > 0 THEN coalesce(cs.quantity, 0) / ms.avg_daily_sales 
                        ELSE 999 
                    END as days_of_coverage,
                    CASE
                        WHEN ms.avg_daily_sales > 0 AND (coalesce(cs.quantity, 0) / ms.avg_daily_sales) < 7 THEN 'critical'
                        WHEN ms.avg_daily_sales > 0 AND (coalesce(cs.quantity, 0) / ms.avg_daily_sales) < 14 THEN 'warning'
                        ELSE 'healthy'
                    END as stock_status
                FROM res_branch rb
                JOIN monthly_sales ms ON ms.branch_id = rb.id
                JOIN current_stock cs ON cs.product_id = ms.product_id
                JOIN stock_location sl ON cs.location_id = sl.id
                JOIN stock_location wsl ON sl.parent_path LIKE wsl.parent_path || '%%'
                JOIN stock_warehouse sw ON sw.view_location_id = wsl.id AND sw.id = rb.warehouse_id
            )
        """ % self._table)


