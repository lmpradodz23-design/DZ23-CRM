# -*- coding: utf-8 -*-
# Webhook de entrada do WhatsApp (Meta Cloud API).
# - GET: verificação do webhook (hub.challenge).
# - POST: valida assinatura HMAC (X-Hub-Signature-256) com o App Secret antes de
#   processar. Loga apenas metadados (sem PII/conteúdo de mensagem).
import hashlib
import hmac
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


def _valid_meta_signature(raw_body, header_sig, app_secret):
    """HMAC-SHA256(app_secret, corpo) == X-Hub-Signature-256 (formato 'sha256=hex')."""
    if not app_secret or not header_sig or not header_sig.startswith("sha256="):
        return False
    expected = hmac.new(app_secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header_sig.split("=", 1)[1])


class DZ23WhatsAppWebhook(http.Controller):

    @http.route("/dz23/whatsapp/webhook", type="http", auth="public",
                methods=["GET"], csrf=False)
    def verify(self, **kw):
        verify_token = request.env["ir.config_parameter"].sudo().get_param(
            "dz23.whatsapp.webhook_verify_token", ""
        )
        mode = kw.get("hub.mode")
        token = kw.get("hub.verify_token")
        challenge = kw.get("hub.challenge", "")
        if mode == "subscribe" and token and verify_token and token == verify_token:
            return request.make_response(challenge)
        return request.make_response("forbidden", status=403)

    @http.route("/dz23/whatsapp/webhook", type="http", auth="public",
                methods=["POST"], csrf=False)
    def receive(self, **_kwargs):
        raw = request.httprequest.get_data() or b""
        header_sig = request.httprequest.headers.get("X-Hub-Signature-256", "")
        app_secret = request.env["ir.config_parameter"].sudo().get_param(
            "dz23.whatsapp.meta_app_secret", ""
        )
        # FAIL-CLOSED: exige assinatura válida da Meta antes de qualquer processamento.
        if not _valid_meta_signature(raw, header_sig, app_secret):
            _logger.warning("WhatsApp webhook REJEITADO (assinatura ausente/inválida).")
            return request.make_response("unauthorized", status=401)

        data = request.get_json_data() or {}
        # Log apenas de metadados (sem número/conteúdo — LGPD).
        try:
            entry = (data.get("entry") or [{}])[0]
            change = (entry.get("changes") or [{}])[0]
            field = change.get("field")
            _logger.info("WhatsApp inbound verificado: field=%s", field)
        except Exception:  # noqa: BLE001
            _logger.info("WhatsApp inbound verificado.")
        # TODO(go-live): vincular a res.partner/crm.lead pelo telefone e criar
        # mensagem no chatter. Só após teste com número real.
        return request.make_response("ok")
