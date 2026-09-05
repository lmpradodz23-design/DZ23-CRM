# -*- coding: utf-8 -*-
from odoo import api, fields, models


class DZ23Integration(models.Model):
    _name = "dz23.integration"
    _description = "DZ23 — Integração"
    _order = "sequence, name"

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    category = fields.Selection(
        selection=[
            ("fiscal", "Fiscal"),
            ("comunicacao", "Comunicação"),
            ("pagamento", "Pagamento"),
            ("ia", "IA"),
            ("marketplace", "Marketplace"),
            ("outro", "Outro"),
        ],
        default="outro",
        required=True,
    )
    description = fields.Text()
    logo = fields.Binary(attachment=True, help="Logomarca oficial do integrador (envie o arquivo).")
    # Chave em ir.config_parameter que indica que a integração foi configurada.
    config_param = fields.Char(help="Chave de ir.config_parameter que sinaliza 'configurado'.")
    docs_url = fields.Char("Documentação")
    official_url = fields.Char("Painel oficial", help="Onde criar a conta e pegar a API.")
    how_to = fields.Html("Como conectar", sanitize=False,
                         help="Passo a passo para obter e ativar a API desta integração.")
    available = fields.Boolean(
        default=True,
        help="Desmarque para integrações que ainda dependem de credencial/homologação externa.",
    )
    status = fields.Selection(
        selection=[
            ("not_configured", "Desconectado"),
            ("configured", "Conectado"),
        ],
        compute="_compute_status",
    )

    @api.depends("config_param")
    def _compute_status(self):
        icp = self.env["ir.config_parameter"].sudo()
        for rec in self:
            val = icp.get_param(rec.config_param) if rec.config_param else False
            rec.status = "configured" if val else "not_configured"

    def action_configure(self):
        """Abre os Ajustes gerais, onde ficam os campos de API de cada integração."""
        self.ensure_one()
        return self.env.ref("base_setup.action_general_configuration").sudo().read()[0]
