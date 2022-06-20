# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from itertools import groupby

from odoo import api, fields, models
from odoo.fields import first


class StockMoveLocationWizard(models.TransientModel):
    _inherit = "wiz.stock.move.location"

    @api.onchange("origin_location_id","product_id","lot_id")
    def onchange_origin_location(self):
        # Get origin_location_disable context key to prevent load all origin
        # location products when user opens the wizard from stock quants to
        # move it to other location.
        if self.product_id:
            self.tracking = self.product_id.tracking
        if (
            not self.env.context.get("origin_location_disable")
            and self.origin_location_id
        ):
            lines = []
            line_model = self.env["wiz.stock.move.location.line"]
            for line_val in self._get_stock_move_location_lines_values():
                if line_val.get('max_quantity') == None or line_val.get("max_quantity",0) <= 0:
                    continue
                line = line_model.create(line_val)
                line.max_quantity = line.get_max_quantity()
                line.reserved_quantity = line.reserved_quantity
                lines.append(line)
            self.update(
                {"stock_move_location_line_ids": [(6, 0, [line.id for line in lines])]}
            )

    product_id = fields.Many2one('product.product',string='Product')
    tracking = fields.Selection([
        ('serial', 'By Unique Serial Number'),
        ('lot', 'By Lots'),
        ('none', 'No Tracking')], 
        string="Tracking", 
        default='none')
    lot_id = fields.Many2one('stock.production.lot',string='Lot/Serial number')


    def _get_group_quants(self):
        location_id = self.origin_location_id
        # Using sql as search_group doesn't support aggregation functions
        # leading to overhead in queries to DB
        if not self.product_id and not self.lot_id:
            query = """
                SELECT product_id, lot_id, SUM(quantity) AS quantity,
                    SUM(reserved_quantity) AS reserved_quantity
                FROM stock_quant
                WHERE location_id = %s
                GROUP BY product_id, lot_id
            """
            self.env.cr.execute(query, (location_id.id,))
        elif self.product_id and not self.lot_id:
            query = """
                SELECT product_id, lot_id, SUM(quantity) AS quantity,
                    SUM(reserved_quantity) AS reserved_quantity
                FROM stock_quant
                WHERE location_id = %s
                AND product_id = %s
                GROUP BY product_id, lot_id
            """
            self.env.cr.execute(query, (location_id.id, self.product_id.id,))
        elif self.product_id and self.lot_id:
            query = """
                SELECT product_id, lot_id, SUM(quantity) AS quantity,
                    SUM(reserved_quantity) AS reserved_quantity
                FROM stock_quant
                WHERE location_id = %s
                AND product_id = %s
                AND lot_id = %s
                GROUP BY product_id, lot_id
            """
            self.env.cr.execute(query, (location_id.id, self.product_id.id, self.lot_id.id, ))
        return self.env.cr.dictfetchall()

