# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    dz23_nfe_status = fields.Selection(
        selection=[
            ("disabled", "Indisponível (não homologado)"),
            ("none", "Não emitida"),
            ("pending", "Processando"),
            ("authorized", "Autorizada"),
            ("error", "Erro"),
        ],
        string="Status NF-e",
        default="disabled",
        copy=False,
        readonly=True,
    )
    dz23_nfe_key = fields.Char("Chave NF-e", copy=False, readonly=True)
    dz23_nfe_danfe_url = fields.Char("DANFE (PDF)", copy=False, readonly=True)
    dz23_nfe_message = fields.Char("Retorno NF-e", copy=False, readonly=True)
    # Disponibilidade real da emissão — falso até adapter homologado (ADR-002).
    # Controla a visibilidade do botão: nada de botão sem backend real.
    dz23_nfe_available = fields.Boolean(
        string="NF-e disponível", compute="_compute_dz23_nfe_available")

    def _compute_dz23_nfe_available(self):
        enabled = self.env["dz23.fiscal"].is_enabled()
        for move in self:
            move.dz23_nfe_available = enabled

    def action_dz23_emit_nfe(self):
        """Emissão fail-closed: recusa até adapter homologado existir (ADR-002).

        Método mantido como defesa; o botão só aparece quando
        dz23.fiscal.is_enabled() for verdadeiro, então esta rota não é
        alcançável pela UI enquanto o fiscal estiver desativado.
        """
        self.ensure_one()
        return self.env["dz23.fiscal"].emit(self)
