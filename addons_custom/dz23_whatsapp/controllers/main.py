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
        svc = request.env["dz23.whatsapp"].sudo()
        number, text = svc._parse_meta_inbound(data)
        if number and text:
            try:
                svc._on_inbound(number, text, data)
            except Exception:  # noqa: BLE001 - webhook nunca deve estourar 500
                _logger.exception("Falha ao processar inbound do WhatsApp")
        else:
            _logger.info("WhatsApp inbound sem texto (evento ignorado).")
        return request.make_response("ok")

    @http.route("/dz23/whatsapp/evolution/webhook", type="http", auth="public",
                methods=["POST"], csrf=False)
    def evolution_webhook(self, **_kwargs):
        """Recebe eventos da Evolution API (MESSAGES_UPSERT) e aciona o agente."""
        raw = request.httprequest.get_data() or b""
        # Valida a apikey (Evolution envia no header 'apikey') se estiver configurada.
        cfg_key = request.env["ir.config_parameter"].sudo().get_param("dz23.whatsapp.evolution_apikey", "")
        req_key = request.httprequest.headers.get("apikey", "")
        if cfg_key and req_key and req_key != cfg_key:
            return request.make_response("unauthorized", status=401)
        import json
        try:
            data = json.loads(raw or b"{}")
        except ValueError:
            data = {}
        svc = request.env["dz23.whatsapp"].sudo()
        number, text = svc._parse_evolution_inbound(data)
        if number and text:
            try:
                svc._on_inbound(number, text, data)
            except Exception:  # noqa: BLE001
                _logger.exception("Falha ao processar inbound Evolution")
        return request.make_response("ok")
