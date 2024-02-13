from odoo import _, fields, models
from odoo.exceptions import UserError


class ValidateAccountMove(models.TransientModel):
    _inherit = "validate.account.move"

    async_post = fields.Boolean(
        "Asynchronous Post", default=False, help="Post moves asynchronously."
    )

    def validate_move(self):
        if self.async_post:
            if self._context.get("active_model") == "account.move":
                domain = [
                    ("id", "in", self._context.get("active_ids", [])),
                    ("state", "=", "draft"),
                ]
            elif self._context.get("active_model") == "account.journal":
                domain = [
                    ("journal_id", "=", self._context.get("active_id")),
                    ("state", "=", "draft"),
                ]
            else:
                raise UserError(_("Missing 'active_model' in context."))

            moves = self.env["account.move"].search(domain).filtered("line_ids")
            if not moves:
                raise UserError(
                    _("There are no journal items in the draft state to post.")
                )
            moves.asynchronous_post = True
            return {"type": "ir.actions.act_window_close"}
        else:
            return super().validate_move()
