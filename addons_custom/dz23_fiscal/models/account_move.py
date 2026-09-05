# -*- coding: utf-8 -*-
from odoo import fields, models
from odoo.tools.translate import _


class AccountMove(models.Model):
    _inherit = "account.move"

    dz23_nfe_status = fields.Selection(
        selection=[
            ("none", "Não emitida"),
            ("pending", "Processando"),
            ("authorized", "Autorizada"),
            ("error", "Erro"),
        ],
        string="Status NF-e",
        default="none",
        copy=False,
        readonly=True,
    )
    dz23_nfe_key = fields.Char("Chave NF-e", copy=False, readonly=True)
    dz23_nfe_danfe_url = fields.Char("DANFE (PDF)", copy=False, readonly=True)
    dz23_nfe_message = fields.Char("Retorno NF-e", copy=False, readonly=True)

    def action_dz23_emit_nfe(self):
        """Emite a NF-e via provedor. Se não configurado, o serviço bloqueia
        com mensagem clara (dependência externa: certificado + conta)."""
        for move in self:
            result = self.env["dz23.fiscal"].emit(move)  # levanta UserError se BLOCKED
            move.dz23_nfe_status = "pending"
            move.dz23_nfe_key = result.get("chave") or result.get("key") or False
            move.dz23_nfe_danfe_url = result.get("danfe_url") or result.get("pdf") or False
            move.dz23_nfe_message = _("Enviada ao provedor.")
        return True
