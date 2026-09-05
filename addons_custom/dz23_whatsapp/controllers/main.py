# -*- coding: utf-8 -*-
# Webhook de entrada do WhatsApp (Meta Cloud API + Evolution API).
# Todos os endpoints são FAIL-CLOSED: sem credencial configurada => 503;
# credencial ausente/inválida => 401; corpo grande => 413; JSON inválido => 400.
# Loga apenas metadados (sem PII/conteúdo de mensagem).
import hashlib
import hmac
import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

# Limite de corpo aceito no webhook (defesa contra abuso/DoS de payload).
_MAX_BODY = 1 * 1024 * 1024  # 1 MiB


def _const_eq(a, b):
    """Comparação de tempo constante entre duas strings (evita timing attack)."""
    return hmac.compare_digest((a or "").encode(), (b or "").encode())


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
        app_secret = request.env["ir.config_parameter"].sudo().get_param(
            "dz23.whatsapp.meta_app_secret", ""
        )
        # FAIL-CLOSED: sem App Secret configurado, o canal Meta está desabilitado.
        if not app_secret:
            _logger.warning("Meta webhook chamado sem App Secret configurado — 503.")
            return request.make_response("service unavailable", status=503)
        raw = request.httprequest.get_data() or b""
        if len(raw) > _MAX_BODY:
            return request.make_response("payload too large", status=413)
        header_sig = request.httprequest.headers.get("X-Hub-Signature-256", "")
        # FAIL-CLOSED: exige assinatura válida da Meta antes de qualquer processamento.
        if not _valid_meta_signature(raw, header_sig, app_secret):
            _logger.warning("WhatsApp webhook REJEITADO (assinatura ausente/inválida).")
            return request.make_response("unauthorized", status=401)

        try:
            data = json.loads(raw or b"{}")
        except ValueError:
            return request.make_response("bad request", status=400)
        if not isinstance(data, dict):
            return request.make_response("bad request", status=400)
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
        cfg_key = request.env["ir.config_parameter"].sudo().get_param(
            "dz23.whatsapp.evolution_apikey", "")
        # FAIL-CLOSED: sem apikey configurada, o canal Evolution está desabilitado.
        if not cfg_key:
            _logger.warning("Evolution webhook chamado sem apikey configurada — 503.")
            return request.make_response("service unavailable", status=503)
        # Credencial obrigatória, comparada em tempo constante (Evolution manda no header 'apikey').
        req_key = request.httprequest.headers.get("apikey", "")
        if not _const_eq(req_key, cfg_key):
            _logger.warning("Evolution webhook REJEITADO (apikey ausente/inválida).")
            return request.make_response("unauthorized", status=401)
        raw = request.httprequest.get_data() or b""
        if len(raw) > _MAX_BODY:
            return request.make_response("payload too large", status=413)
        try:
            data = json.loads(raw or b"{}")
        except ValueError:
            return request.make_response("bad request", status=400)
        if not isinstance(data, dict):
            return request.make_response("bad request", status=400)
        svc = request.env["dz23.whatsapp"].sudo()
        number, text = svc._parse_evolution_inbound(data)
        if number and text:
            try:
                svc._on_inbound(number, text, data)
            except Exception:  # noqa: BLE001
                _logger.exception("Falha ao processar inbound Evolution")
        return request.make_response("ok")
