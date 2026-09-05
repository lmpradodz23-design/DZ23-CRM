# -*- coding: utf-8 -*-
# Serviço de envio de WhatsApp — dispatch por provedor.
# Credenciais lidas de ir.config_parameter (definidas em Ajustes, no servidor).
# NENHUM segredo é hardcoded aqui.
import logging
import re

import requests

from odoo import api, models
from odoo.exceptions import UserError
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)
_TIMEOUT = 15


def _digits(v):
    return re.sub(r"\D", "", v or "")


def _e164_br(number):
    """Normaliza para dígitos E.164; assume Brasil (55) quando faltar DDI."""
    raw = _digits(number)
    if not raw:
        return ""
    if not raw.startswith("55") and len(raw) in (10, 11):
        raw = "55" + raw
    return raw


class DZ23WhatsApp(models.AbstractModel):
    _name = "dz23.whatsapp"
    _description = "DZ23 — Serviço de envio de WhatsApp (plugável)"

    def _param(self, key, default=""):
        return self.env["ir.config_parameter"].sudo().get_param(key, default)

    def _provider(self):
        return (self._param("dz23.whatsapp_provider", "meta_cloud") or "meta_cloud").strip()

    # ---------- API pública ----------
    @api.model
    def send_text(self, number, body):
        """Envia uma mensagem de texto simples. Retorna o JSON do provedor.

        Levanta UserError com mensagem amigável em caso de config faltando/erro.
        """
        to = _e164_br(number)
        if not to:
            raise UserError(_("Número de WhatsApp inválido."))
        if not body:
            raise UserError(_("Mensagem vazia."))
        provider = self._provider()
        dispatch = {
            "meta_cloud": self._send_meta_cloud,
            "twilio": self._send_twilio,
            "evolution": self._send_evolution,
        }.get(provider)
        if not dispatch:
            raise UserError(_("Provedor de WhatsApp não suportado: %s") % provider)
        return dispatch(to, body)

    def _post(self, url, **kwargs):
        try:
            resp = requests.post(url, timeout=_TIMEOUT, **kwargs)
        except requests.exceptions.RequestException as e:
            _logger.warning("DZ23 WhatsApp erro de rede: %s", e)
            raise UserError(_("Falha de rede ao enviar WhatsApp."))
        if resp.status_code >= 400:
            _logger.info("DZ23 WhatsApp %s -> %s: %s", url, resp.status_code, resp.text[:500])
            raise UserError(_("O provedor recusou o envio (código %s).") % resp.status_code)
        try:
            return resp.json()
        except ValueError:
            return {"raw": resp.text}

    # ---------- Adaptadores ----------
    def _send_meta_cloud(self, to, body):
        # Meta WhatsApp Cloud API. Token + phone_number_id vêm do config (servidor).
        token = self._param("dz23.whatsapp.meta_token")
        phone_id = self._param("dz23.whatsapp.meta_phone_id")
        version = self._param("dz23.whatsapp.meta_api_version", "v20.0")
        if not token or not phone_id:
            raise UserError(_("Configure o token e o phone_number_id da Meta em Ajustes."))
        url = "https://graph.facebook.com/%s/%s/messages" % (version, phone_id)
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": body},
        }
        return self._post(url, headers={"Authorization": "Bearer %s" % token}, json=payload)

    def _send_twilio(self, to, body):
        # Twilio WhatsApp. Account SID + Auth Token + número 'from' do config.
        sid = self._param("dz23.whatsapp.twilio_sid")
        token = self._param("dz23.whatsapp.twilio_token")
        from_ = self._param("dz23.whatsapp.twilio_from")  # ex.: +14155238886
        if not sid or not token or not from_:
            raise UserError(_("Configure SID, token e número 'from' do Twilio em Ajustes."))
        url = "https://api.twilio.com/2010-04-01/Accounts/%s/Messages.json" % sid
        data = {
            "From": "whatsapp:%s" % from_ if not from_.startswith("whatsapp:") else from_,
            "To": "whatsapp:+%s" % to,
            "Body": body,
        }
        return self._post(url, data=data, auth=(sid, token))

    def _send_evolution(self, to, body):
        # Evolution API (não-oficial). base_url + instance + apikey do config.
        base = (self._param("dz23.whatsapp.evolution_base") or "").rstrip("/")
        instance = self._param("dz23.whatsapp.evolution_instance")
        apikey = self._param("dz23.whatsapp.evolution_apikey")
        if not base or not instance or not apikey:
            raise UserError(_("Configure base, instância e apikey da Evolution em Ajustes."))
        url = "%s/message/sendText/%s" % (base, instance)
        payload = {"number": to, "text": body}
        return self._post(url, headers={"apikey": apikey}, json=payload)
