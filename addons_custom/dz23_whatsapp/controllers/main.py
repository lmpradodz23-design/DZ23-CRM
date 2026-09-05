# -*- coding: utf-8 -*-
# Webhook de entrada do WhatsApp (Meta Cloud API).
# - GET: verificação do webhook (hub.challenge) da Meta.
# - POST: recebe eventos (mensagens de sessão). Registra em log.
# NOTA: o processamento completo (vincular ao lead/partner, criar mensagem no
# chatter) precisa de teste com o número/instância reais — marcado como TODO.
import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class DZ23WhatsAppWebhook(http.Controller):

    @http.route("/dz23/whatsapp/webhook", type="http", auth="public",
                methods=["GET"], csrf=False)
    def verify(self, **kw):
        # Meta chama com hub.mode/hub.verify_token/hub.challenge
        verify_token = request.env["ir.config_parameter"].sudo().get_param(
            "dz23.whatsapp.webhook_verify_token", ""
        )
        mode = kw.get("hub.mode")
        token = kw.get("hub.verify_token")
        challenge = kw.get("hub.challenge", "")
        if mode == "subscribe" and token and token == verify_token:
            return request.make_response(challenge)
        return request.make_response("forbidden", status=403)

    @http.route("/dz23/whatsapp/webhook", type="http", auth="public",
                methods=["POST"], csrf=False)
    def receive(self, **kw):
        try:
            payload = json.loads(request.httprequest.data or b"{}")
        except ValueError:
            payload = {}
        # TODO (testar com número real): extrair mensagem e vincular ao
        # res.partner/crm.lead pelo telefone, criando mensagem no chatter.
        _logger.info("DZ23 WhatsApp inbound: %s", json.dumps(payload)[:1000])
        return request.make_response("ok")
