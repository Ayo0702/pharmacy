from odoo import models, fields, api, _

class ResUsers(models.Model):
    _inherit = 'res.users'

    default_branch_id = fields.Many2one('res.branch', string='Default Branch')


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_controlled = fields.Boolean(string='Is Controlled Drug', default=False)


class PosOrder(models.Model):
    _inherit = 'pos.order'

    branch_id = fields.Many2one(
        'res.branch', string='Branch',
        default=lambda self: self.env.user.default_branch_id or self.env['res.branch'].search([], limit=1),
        index=True
    )

    @api.model
    def _order_fields(self, ui_order):
        res = super(PosOrder, self)._order_fields(ui_order)
        # Handle field mapping from UI if needed, but here we use backend default
        # or it can be passed from POS frontend in a real implementation.
        return res

    def _prepare_invoice_vals(self):
        vals = super(PosOrder, self)._prepare_invoice_vals()
        if self.branch_id:
            vals['branch_id'] = self.branch_id.id
        return vals

    def _create_order_picking(self):
        res = super(PosOrder, self)._create_order_picking()
        for order in self:
            if order.branch_id and order.picking_ids:
                order.picking_ids.write({'branch_id': order.branch_id.id})
        return res

    def _create_account_move_line(self, session_move, reversed_move=False):
        """
        Override to handle HMO dual receivables.
        Modified lines for HMO payments to point to the HMO receivable account.
        """
        res = super(PosOrder, self)._create_account_move_line(session_move, reversed_move)
        
        for order in self:
            hmo_payments = order.payment_ids.filtered(lambda p: p.payment_method_id.is_hmo)
            if not hmo_payments:
                continue
                
            # Find the account move and its lines
            # In Odoo 18, this method might return created lines or modify session_move directly.
            # Assuming we need to adjust the receivable lines created for these payments.
            for payment in hmo_payments:
                hmo_account = payment.payment_method_id.hmo_receivable_account_id
                if not hmo_account:
                    continue
                
                # Logic to find the corresponding receivable line in session_move
                # and swap its account_id.
                # Since super() already created lines, we update them.
                aml_to_update = session_move.line_ids.filtered(
                    lambda l: l.payment_id == payment.id and l.account_id != hmo_account
                )
                if aml_to_update:
                    aml_to_update.write({'account_id': hmo_account.id})
        
        return res


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    branch_id = fields.Many2one('res.branch', string='Branch', index=True)


class AccountMove(models.Model):
    _inherit = 'account.move'

    branch_id = fields.Many2one('res.branch', string='Branch', index=True)
