# -*- coding: utf-8 -*-
# Webhook Woovi: confirma o pagamento PIX.
# SEGURANÇA (fail-closed): só processa se a assinatura RSA do corpo for válida
# contra a chave pública da Woovi (ir.config_parameter dz23.woovi.webhook_pubkey).
# Sem chave configurada OU assinatura inválida => 401 e NÃO confirma pagamento.
import base64
import binascii
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

_PUBKEY_PARAM = "dz23.woovi.webhook_pubkey"


def _verify_woovi_signature(raw_body, signature_b64, pubkey_pem):
    """Verifica RSA-SHA256 (PKCS1v15) do corpo bruto com a chave pública Woovi."""
    if not pubkey_pem or not signature_b64:
        return False
    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding
        public_key = serialization.load_pem_public_key(pubkey_pem.encode())
        public_key.verify(
            base64.b64decode(signature_b64),
            raw_body,
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return True
    except (ValueError, binascii.Error, Exception):  # noqa: BLE001 - falha = inválido
        return False


class WooviController(http.Controller):

    @http.route("/payment/woovi/webhook", type="http", auth="public",
                methods=["POST"], csrf=False)
    def woovi_webhook(self, **_kwargs):
        raw = request.httprequest.get_data() or b""
        signature = request.httprequest.headers.get("x-webhook-signature", "")
        pubkey = request.env["ir.config_parameter"].sudo().get_param(_PUBKEY_PARAM, "")

        # FAIL-CLOSED: sem chave pública configurada ou assinatura inválida, recusa.
        if not _verify_woovi_signature(raw, signature, pubkey):
            _logger.warning("Woovi webhook REJEITADO (assinatura ausente/inválida).")
            return request.make_response("unauthorized", status=401)

        data = request.get_json_data()
        charge = (data or {}).get("charge") or {}
        correlation = charge.get("correlationID")
        _logger.info("Woovi webhook OK: correlationID=%s status=%s", correlation, charge.get("status"))
        if correlation:
            tx_sudo = request.env["payment.transaction"].sudo()._search_by_reference("woovi", data)
            if tx_sudo:
                tx_sudo._process("woovi", data)
        return request.make_response("ok")
