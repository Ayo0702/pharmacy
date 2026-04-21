from odoo import models, fields, api

class ResBranch(models.Model):
    _name = 'res.branch'
    _description = 'Pharmacy Branch'

    name = fields.Char(string='Branch Name', required=True)
    company_id = fields.Many2one(
        'res.company', string='Company', 
        required=True, default=lambda self: self.env.company
    )
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')
    pos_config_id = fields.Many2one('pos.config', string='POS Configuration')
    is_active = fields.Boolean(string='Active', default=True)

    _sql_constraints = [
        ('name_uniq', 'unique (name, company_id)', 'Branch name must be unique per company!')
    ]
