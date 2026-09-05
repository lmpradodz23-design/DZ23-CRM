# -*- coding: utf-8 -*-
# Canal de mensageria multi-tenant. UM canal pertence a EXATAMENTE UMA empresa
# (company_id) e carrega as PRÓPRIAS credenciais + prompt do agente — nada de
# ir.config_parameter global. O webhook resolve o canal por um token opaco e
# autentica por canal. Todo o processamento roda no escopo da empresa do canal.
import logging
import re
import secrets

import requests

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
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


class DZ23Channel(models.Model):
    _name = "dz23.channel"
    _description = "DZ23 — Canal de mensageria (multi-tenant, por empresa)"
    _order = "company_id, name"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company", required=True, index=True,
        default=lambda self: self.env.company,
        help="Empresa dona deste canal. Todo lead/evento/pedido nasce nela.")
    provider = fields.Selection(
        [("evolution", "Evolution API"), ("meta_cloud", "Meta WhatsApp Cloud"),
         ("twilio", "Twilio")],
        required=True, default="evolution")
    # Token opaco que identifica o canal na URL do webhook (não é segredo de
    # autenticação — a auth é por apikey/app_secret do canal — mas evita expor
    # instância/empresa e permite rotear sem varredura global).
    webhook_token = fields.Char(
        required=True, copy=False, index=True, readonly=True,
        default=lambda self: secrets.token_urlsafe(24))

    # Evolution
    evo_base = fields.Char("Evolution base URL")
    evo_instance = fields.Char("Evolution instance")
    evo_apikey = fields.Char("Evolution apikey")
    # Meta Cloud
    meta_phone_id = fields.Char("Meta phone_number_id")
    meta_token = fields.Char("Meta token")
    meta_api_version = fields.Char("Meta API version", default="v20.0")
    meta_app_secret = fields.Char("Meta App Secret")
    meta_verify_token = fields.Char("Meta verify token")
    # Twilio
    twilio_sid = fields.Char("Twilio SID")
    twilio_token = fields.Char("Twilio token")
    twilio_from = fields.Char("Twilio from")

    # Agente
    agent_autoreply = fields.Boolean("Auto-resposta do agente", default=True)
    agent_prompt = fields.Text("Personalidade/instruções do agente")

    _webhook_token_uniq = models.Constraint(
        "unique(webhook_token)", "Token de webhook duplicado.")

    @api.constrains("provider", "evo_instance", "company_id")
    def _check_evo_instance_unique(self):
        for ch in self:
            if ch.provider == "evolution" and ch.evo_instance:
                dup = self.search([
                    ("id", "!=", ch.id), ("provider", "=", "evolution"),
                    ("evo_instance", "=", ch.evo_instance)], limit=1)
                if dup:
                    raise ValidationError(
                        _("A instância Evolution '%s' já está em uso por outro canal.")
                        % ch.evo_instance)

    # ---------- resolução (usada pelo webhook) ----------
    @api.model
    def _resolve_by_token(self, token):
        """Acha o canal pelo token opaco da URL. Sudo interno; escopo aplicado depois."""
        if not token:
            return self.browse()
        return self.sudo().search([("webhook_token", "=", token)], limit=1)

    def _scoped(self):
        """Retorna self no contexto da empresa do canal (isola dados por tenant)."""
        self.ensure_one()
        return self.with_company(self.company_id).with_context(
            allowed_company_ids=[self.company_id.id])

    # ---------- envio ----------
    def send_text(self, number, body):
        self.ensure_one()
        to = _e164_br(number)
        if not to:
            raise UserError(_("Número de WhatsApp inválido."))
        if not body:
            raise UserError(_("Mensagem vazia."))
        return {
            "evolution": self._send_evolution,
            "meta_cloud": self._send_meta_cloud,
            "twilio": self._send_twilio,
        }[self.provider](to, body)

    def _post(self, url, **kwargs):
        try:
            resp = requests.post(url, timeout=_TIMEOUT, **kwargs)
        except requests.exceptions.RequestException as e:
            _logger.warning("DZ23 WhatsApp erro de rede: %s", e)
            raise UserError(_("Falha de rede ao enviar WhatsApp."))
        if resp.status_code >= 400:
            _logger.info("DZ23 WhatsApp %s -> %s", url, resp.status_code)
            raise UserError(_("O provedor recusou o envio (código %s).") % resp.status_code)
        try:
            return resp.json()
        except ValueError:
            return {"raw": resp.text}

    def _send_evolution(self, to, body):
        if not (self.evo_base and self.evo_instance and self.evo_apikey):
            raise UserError(_("Canal Evolution incompleto (base/instância/apikey)."))
        url = "%s/message/sendText/%s" % (self.evo_base.rstrip("/"), self.evo_instance)
        return self._post(url, headers={"apikey": self.evo_apikey},
                          json={"number": to, "text": body})

    def _send_meta_cloud(self, to, body):
        if not (self.meta_token and self.meta_phone_id):
            raise UserError(_("Canal Meta incompleto (token/phone_id)."))
        url = "https://graph.facebook.com/%s/%s/messages" % (
            self.meta_api_version or "v20.0", self.meta_phone_id)
        return self._post(url, headers={"Authorization": "Bearer %s" % self.meta_token},
                          json={"messaging_product": "whatsapp", "to": to,
                                "type": "text", "text": {"body": body}})

    def _send_twilio(self, to, body):
        if not (self.twilio_sid and self.twilio_token and self.twilio_from):
            raise UserError(_("Canal Twilio incompleto (sid/token/from)."))
        url = "https://api.twilio.com/2010-04-01/Accounts/%s/Messages.json" % self.twilio_sid
        frm = self.twilio_from if self.twilio_from.startswith("whatsapp:") else "whatsapp:%s" % self.twilio_from
        return self._post(url, data={"From": frm, "To": "whatsapp:+%s" % to, "Body": body},
                          auth=(self.twilio_sid, self.twilio_token))

    # ---------- inbound (base: só registra; dz23_agent sobrescreve) ----------
    def handle_inbound(self, number, text, raw=None):
        """Processa uma mensagem recebida NO ESCOPO da empresa do canal.
        Base apenas registra; o módulo dz23_agent sobrescreve para atender."""
        self.ensure_one()
        _logger.info("[canal %s/%s] inbound de %s: %s",
                     self.id, self.company_id.display_name, number, (text or "")[:80])
        return False

    # ---------- Evolution: provisionamento por canal ----------
    def _evo_req(self, method, path, **kwargs):
        self.ensure_one()
        if not (self.evo_base and self.evo_apikey):
            raise UserError(_("Configure a base URL e a apikey da Evolution no canal."))
        url = "%s%s" % (self.evo_base.rstrip("/"), path)
        try:
            resp = requests.request(
                method, url, timeout=_TIMEOUT,
                headers={"apikey": self.evo_apikey, "Content-Type": "application/json"},
                **kwargs)
        except requests.exceptions.RequestException as e:
            raise UserError(_("Não foi possível falar com o servidor Evolution: %s") % e)
        try:
            return resp.json()
        except ValueError:
            return {"raw": resp.text}

    def _webhook_url(self, kind):
        base = (self.env["ir.config_parameter"].sudo().get_param("web.base.url")
                or "http://localhost:8069").rstrip("/")
        return "%s/dz23/whatsapp/%s/webhook/%s" % (base, kind, self.webhook_token)

    def action_evolution_connect(self):
        """Cria a instância (se preciso), configura o webhook tokenizado e devolve o QR."""
        self.ensure_one()
        if not self.evo_instance:
            self.evo_instance = "dz23_%s_%s" % (self.company_id.id, self.id)
        self._evo_req("POST", "/instance/create", json={
            "instanceName": self.evo_instance, "integration": "WHATSAPP-BAILEYS", "qrcode": True})
        # webhook tokenizado + apikey no header (endpoint é fail-closed)
        self._evo_req("POST", "/webhook/set/%s" % self.evo_instance, json={
            "webhook": {
                "enabled": True,
                "url": self._webhook_url("evolution"),
                "webhookByEvents": False,
                "events": ["MESSAGES_UPSERT"],
                "headers": {"apikey": self.evo_apikey, "Content-Type": "application/json"},
            }})
        data = self._evo_req("GET", "/instance/connect/%s" % self.evo_instance)
        qr = data.get("base64") or (data.get("qrcode") or {}).get("base64") or ""
        return {"instance": self.evo_instance, "qr": qr, "webhook": self._webhook_url("evolution")}
