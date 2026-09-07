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
    how_to = fields.Html(
        "Como conectar",
        sanitize=True,
        help="Passo a passo para obter e ativar a API desta integração.",
    )
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
        """Abre os Ajustes já na aba certa da integração (IA/WhatsApp/NF-e) ou,
        para pagamentos, a lista de provedores de pagamento."""
        self.ensure_one()
        cp = self.config_param or ""
        # Pagamento -> lista de provedores de pagamento
        if self.category == "pagamento":
            act = self.env.ref("payment.action_payment_provider", raise_if_not_found=False)
            if act:
                return act.sudo().read()[0]
        # Descobrir a aba (app) de Ajustes pela chave/categoria
        module = False
        if cp.startswith("dz23.ai") or self.category == "ia":
            module = "dz23_ai"
        elif cp.startswith("dz23.whatsapp"):
            module = "dz23_whatsapp"
        elif cp.startswith("dz23.nfe") or self.category == "fiscal":
            module = "dz23_fiscal"
        action = self.env.ref("base_setup.action_general_configuration").sudo().read()[0]
        if module:
            action["context"] = {"module": module}
        return action
