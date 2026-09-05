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

    # ---------- Entrada (inbound) ----------
    @api.model
    def _parse_meta_inbound(self, data):
        """Extrai (número, texto) de um payload de webhook da Meta Cloud API."""
        try:
            value = data["entry"][0]["changes"][0]["value"]
            msg = (value.get("messages") or [{}])[0]
            number = msg.get("from")
            text = (msg.get("text") or {}).get("body")
            return number, text
        except Exception:  # noqa: BLE001
            return None, None

    def _on_inbound(self, number, text, raw=None):
        """Gancho chamado quando chega mensagem. Base: só registra.
        O módulo dz23_agent sobrescreve para responder com IA e agendar."""
        _logger.info("WhatsApp inbound de %s: %s", number, (text or "")[:80])
        return False

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
        instance = self._param("dz23.whatsapp.evolution_instance") or self._evo_instance_name()
        apikey = self._param("dz23.whatsapp.evolution_apikey")
        if not base or not instance or not apikey:
            raise UserError(_("Configure base, instância e apikey da Evolution em Ajustes."))
        url = "%s/message/sendText/%s" % (base, instance)
        payload = {"number": to, "text": body}
        return self._post(url, headers={"apikey": apikey}, json=payload)

    # ---------- Evolution: provisionamento (criar instância + QR) ----------
    def _evo_instance_name(self):
        return self._param("dz23.whatsapp.evolution_instance") or ("dz23_%s" % self.env.cr.dbname)

    def _evo_base_apikey(self):
        base = (self._param("dz23.whatsapp.evolution_base") or "").rstrip("/")
        apikey = self._param("dz23.whatsapp.evolution_apikey")
        if not base or not apikey:
            raise UserError(_("Configure a base URL e a apikey da Evolution em Ajustes."))
        return base, apikey

    def _evo_request(self, method, path, apikey, **kwargs):
        base, _ak = self._evo_base_apikey() if not apikey else (self._param("dz23.whatsapp.evolution_base").rstrip("/"), apikey)
        url = "%s%s" % (base, path)
        try:
            resp = requests.request(method, url, timeout=_TIMEOUT,
                                    headers={"apikey": apikey, "Content-Type": "application/json"},
                                    **kwargs)
        except requests.exceptions.RequestException as e:
            raise UserError(_("Não foi possível falar com o servidor Evolution: %s") % e)
        if resp.status_code >= 400 and resp.status_code != 403:
            _logger.info("Evolution %s %s -> %s: %s", method, url, resp.status_code, resp.text[:300])
        try:
            return resp.json()
        except ValueError:
            return {"raw": resp.text}

    @api.model
    def evolution_connect(self):
        """Cria a instância (se não existir), configura o webhook e retorna o QR (base64)."""
        base, apikey = self._evo_base_apikey()
        instance = self._evo_instance_name()
        # 1) cria a instância (idempotente: se já existe, a API retorna erro tratável)
        self._evo_request("POST", "/instance/create", apikey, json={
            "instanceName": instance,
            "integration": "WHATSAPP-BAILEYS",
            "qrcode": True,
        })
        # salva o nome da instância no config
        self.env["ir.config_parameter"].sudo().set_param("dz23.whatsapp.evolution_instance", instance)
        # 2) configura o webhook de entrada -> nosso endpoint.
        # Envia a apikey como HEADER no callback: o endpoint é FAIL-CLOSED e
        # exige esse header (401 sem / 200 com), então o provisionamento precisa
        # configurá-lo aqui para o callback da Evolution ser aceito.
        webhook_url = "%s/dz23/whatsapp/evolution/webhook" % (
            (self._param("web.base.url") or "http://localhost:8069").rstrip("/"))
        self._evo_request("POST", "/webhook/set/%s" % instance, apikey, json={
            "webhook": {
                "enabled": True,
                "url": webhook_url,
                "webhookByEvents": False,
                "events": ["MESSAGES_UPSERT"],
                "headers": {"apikey": apikey, "Content-Type": "application/json"},
            },
        })
        # 3) pega o QR para conectar
        data = self._evo_request("GET", "/instance/connect/%s" % instance, apikey)
        qr = data.get("base64") or (data.get("qrcode") or {}).get("base64") or ""
        return {"instance": instance, "qr": qr, "webhook": webhook_url}

    # ---------- Evolution: leitura de mensagem recebida ----------
    @api.model
    def _parse_evolution_inbound(self, data):
        """Extrai (número, texto) de um evento MESSAGES_UPSERT da Evolution."""
        try:
            d = data.get("data") or {}
            key = d.get("key") or {}
            if key.get("fromMe"):
                return None, None  # ignora o que nós mesmos enviamos
            jid = key.get("remoteJid") or ""
            number = jid.split("@")[0]
            msg = d.get("message") or {}
            text = (msg.get("conversation")
                    or (msg.get("extendedTextMessage") or {}).get("text"))
            return number, text
        except Exception:  # noqa: BLE001
            return None, None
