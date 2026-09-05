# -*- coding: utf-8 -*-
# Serviço de emissão de NF-e via provedor de terceiros.
# Provedores suportados (config): focusnfe | nfeio | nuvemfiscal.
# As credenciais/token e o certificado ficam no servidor (config), nunca no código.
import logging

import requests

from odoo import api, models
from odoo.exceptions import UserError
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)
_TIMEOUT = 30

# Endpoints base por provedor (produção). Sandbox é configurável.
PROVIDER_BASE = {
    "focusnfe": "https://api.focusnfe.com.br",
    "nfeio": "https://api.nfe.io",
    "nuvemfiscal": "https://api.nuvemfiscal.com.br",
}


class DZ23Fiscal(models.AbstractModel):
    _name = "dz23.fiscal"
    _description = "DZ23 — Serviço de emissão de NF-e via provedor"

    def _cfg(self, key, default=""):
        return self.env["ir.config_parameter"].sudo().get_param(key, default)

    def _provider(self):
        return (self._cfg("dz23.nfe_provider", "") or "").strip()

    def _require_config(self):
        provider = self._provider()
        token = self._cfg("dz23.nfe_token")
        if not provider or not token:
            # Dependência externa real: sem provedor/token/certificado não há emissão.
            raise UserError(_(
                "Emissão de NF-e indisponível: configure o provedor e o token em "
                "Ajustes, e envie o certificado e-CNPJ A1 ao provedor. "
                "(BLOCKED: requer certificado + conta do provedor + validação contábil.)"
            ))
        base = self._cfg("dz23.nfe_base") or PROVIDER_BASE.get(provider)
        if not base:
            raise UserError(_("Base do provedor de NF-e não configurada."))
        return provider, token, base.rstrip("/")

    @api.model
    def emit(self, invoice):
        """Monta o payload a partir da fatura e chama a API do provedor.

        Retorna o JSON do provedor. Levanta UserError amigável se não configurado
        (dependência externa) ou em erro de rede/HTTP.
        """
        provider, token, base = self._require_config()
        payload = self._build_payload(invoice)
        url = "%s/v2/nfe" % base  # rota genérica; ajustar por provedor no go-live
        try:
            resp = requests.post(
                url, json=payload, timeout=_TIMEOUT,
                headers={"Authorization": token, "Content-Type": "application/json"},
            )
        except requests.exceptions.RequestException as e:
            _logger.warning("DZ23 NF-e erro de rede (%s): %s", provider, e)
            raise UserError(_("Falha de rede ao contatar o provedor de NF-e."))
        if resp.status_code >= 400:
            _logger.info("DZ23 NF-e %s -> %s: %s", url, resp.status_code, resp.text[:500])
            raise UserError(_("O provedor recusou a emissão (código %s).") % resp.status_code)
        try:
            return resp.json()
        except ValueError:
            return {"raw": resp.text}

    def _build_payload(self, invoice):
        """Payload mínimo genérico a partir da fatura (account.move)."""
        partner = invoice.partner_id
        return {
            "natureza_operacao": "Venda",
            "referencia": invoice.name or ("INV-%s" % invoice.id),
            "cnpj_emitente": (invoice.company_id.vat or ""),
            "destinatario": {
                "nome": partner.name or "",
                "cnpj_cpf": partner.vat or "",
                "email": partner.email or "",
            },
            "valor_total": invoice.amount_total,
            "itens": [
                {
                    "descricao": line.name or (line.product_id.display_name or ""),
                    "quantidade": line.quantity,
                    "valor_unitario": line.price_unit,
                }
                for line in invoice.invoice_line_ids
                if line.display_type in (False, "product")
            ],
        }
