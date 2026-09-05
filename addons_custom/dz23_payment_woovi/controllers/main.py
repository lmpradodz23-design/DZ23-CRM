# -*- coding: utf-8 -*-
# Webhook Woovi: confirma o pagamento PIX.
# NOTA: a verificação de assinatura (chave pública RSA da Woovi) deve ser
# ativada em produção — marcada como TODO até termos a config/sandbox.
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class WooviController(http.Controller):

    @http.route("/payment/woovi/webhook", type="http", auth="public",
                methods=["POST"], csrf=False)
    def woovi_webhook(self, **_kwargs):
        data = request.get_json_data()
        _logger.info("Woovi webhook recebido: %s", str(data)[:1000])
        charge = (data or {}).get("charge")
        if charge and charge.get("correlationID"):
            tx_sudo = request.env["payment.transaction"].sudo()._search_by_reference(
                "woovi", data
            )
            if tx_sudo:
                # TODO(produção): validar assinatura x-webhook-signature (RSA) antes de processar.
                tx_sudo._process("woovi", data)
        return request.make_response("ok")
