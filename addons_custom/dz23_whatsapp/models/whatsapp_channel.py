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


def ensure_bot_user(env):
    """Cria (idempotente) o usuário técnico dz23_whatsapp_bot via ORM (aplica os
    defaults dos campos, evitando NOT NULL em res_partner) e registra o xmlid.
    Chamado no post_init (instalação) e na migração (upgrade)."""
    imd = env["ir.model.data"]
    existing = imd.search(
        [("module", "=", "dz23_whatsapp"), ("name", "=", "user_dz23_bot")], limit=1
    )
    if existing:
        return env["res.users"].browse(existing.res_id)
    groups = [env.ref("base.group_user").id]
    salesman = env.ref("sales_team.group_sale_salesman", raise_if_not_found=False)
    if salesman:
        groups.append(salesman.id)
    vals = {
        "name": "DZ23 WhatsApp Bot",
        "login": "dz23_whatsapp_bot",
        "share": False,
        "group_ids": [(6, 0, groups)],
    }
    # Alguns campos NOT NULL de res.partner (ex.: autopost_bills do account) não
    # recebem default neste create em tempo de load; preenche defensivamente.
    Partner = env["res.partner"]
    if "autopost_bills" in Partner._fields:
        vals["autopost_bills"] = (
            Partner.default_get(["autopost_bills"]).get("autopost_bills") or "never"
        )
    bot = env["res.users"].with_context(no_reset_password=True).create(vals)
    imd.create(
        {
            "module": "dz23_whatsapp",
            "name": "user_dz23_bot",
            "model": "res.users",
            "res_id": bot.id,
            "noupdate": True,
        }
    )
    return bot


class DZ23Channel(models.Model):
    _name = "dz23.channel"
    _description = "DZ23 — Canal de mensageria (multi-tenant, por empresa)"
    _order = "company_id, name"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        index=True,
        default=lambda self: self.env.company,
        help="Empresa dona deste canal. Todo lead/evento/pedido nasce nela.",
    )
    provider = fields.Selection(
        [
            ("evolution", "Evolution API"),
            ("meta_cloud", "Meta WhatsApp Cloud"),
            ("twilio", "Twilio"),
        ],
        required=True,
        default="evolution",
    )
    # Identificador do canal no provedor (instance/phone_id/from), único por
    # provedor. Base para resolver o canal e validar o payload.
    provider_channel_id = fields.Char(
        compute="_compute_provider_channel_id",
        store=True,
        index=True,
        string="ID do canal no provedor",
    )
    # Token opaco que identifica o canal na URL do webhook (não é segredo de
    # autenticação — a auth é por apikey/app_secret do canal — mas evita expor
    # instância/empresa e permite rotear sem varredura global).
    # groups=group_system: segredos legíveis só por admin (não por group_user
    # comum via ORM/XML-RPC). O envio/webhook lê via sudo (MED-1).
    webhook_token = fields.Char(
        required=True,
        copy=False,
        index=True,
        readonly=True,
        groups="base.group_system",
        default=lambda self: secrets.token_urlsafe(24),
    )
    # Segredo INDEPENDENTE da chave administrativa do provedor, usado só para
    # autenticar o callback (header X-DZ23-Callback). Rotacionável por canal.
    callback_secret = fields.Char(
        required=True,
        copy=False,
        readonly=True,
        groups="base.group_system",
        default=lambda self: secrets.token_urlsafe(32),
    )

    # Evolution
    evo_base = fields.Char("Evolution base URL")
    evo_instance = fields.Char("Evolution instance")
    evo_apikey = fields.Char("Evolution apikey", groups="base.group_system")
    # Meta Cloud
    meta_phone_id = fields.Char("Meta phone_number_id")
    meta_token = fields.Char("Meta token", groups="base.group_system")
    meta_api_version = fields.Char("Meta API version", default="v20.0")
    meta_app_secret = fields.Char("Meta App Secret", groups="base.group_system")
    meta_verify_token = fields.Char("Meta verify token", groups="base.group_system")
    # Twilio
    twilio_sid = fields.Char("Twilio SID")
    twilio_token = fields.Char("Twilio token", groups="base.group_system")
    twilio_from = fields.Char("Twilio from")

    # Agente — o valor é POR CANAL; os Ajustes globais só definem o PADRÃO
    # aplicado a canais NOVOS (evita o controle enganoso apontado no QA).
    agent_autoreply = fields.Boolean(
        "Auto-resposta do agente", default=lambda self: self._default_agent_autoreply()
    )
    agent_prompt = fields.Text(
        "Personalidade/instruções do agente",
        default=lambda self: (
            self.env["ir.config_parameter"].sudo().get_param("dz23.agent.prompt", "")
        ),
    )

    @api.model
    def _default_agent_autoreply(self):
        val = self.env["ir.config_parameter"].sudo().get_param("dz23.agent.autoreply", "1")
        return (val or "1") not in ("0", "False", "false", "")

    _webhook_token_uniq = models.Constraint("unique(webhook_token)", "Token de webhook duplicado.")
    _provider_channel_uniq = models.Constraint(
        "unique(provider, provider_channel_id)",
        "Já existe um canal com esse provedor e identificador.",
    )

    @api.depends("provider", "evo_instance", "meta_phone_id", "twilio_from")
    def _compute_provider_channel_id(self):
        for ch in self:
            ch.provider_channel_id = {
                "evolution": ch.evo_instance,
                "meta_cloud": ch.meta_phone_id,
                "twilio": ch.twilio_from,
            }.get(ch.provider) or False

    # ---- usuário técnico (para sair do sudo no processamento) -------------
    def _bot_user(self):
        """Usuário técnico; criado sob demanda em runtime (quando o account já
        está carregado), nunca em tempo de load do módulo."""
        user = self.env.ref("dz23_whatsapp.user_dz23_bot", raise_if_not_found=False)
        if not user:
            user = ensure_bot_user(self.env)
        return user

    def _ensure_bot_in_company(self):
        """Garante que o usuário técnico existe e pertence à empresa do canal."""
        bot = self.sudo()._bot_user()
        if not bot:
            return
        for ch in self:
            if ch.company_id and ch.company_id.id not in bot.company_ids.ids:
                bot.write({"company_ids": [(4, ch.company_id.id)]})

    def _processing_self(self):
        """Retorna o canal para processar inbound: usuário TÉCNICO (não sudo),
        no escopo estrito da empresa do canal, sujeito às record rules."""
        self.ensure_one()
        self.sudo()._ensure_bot_in_company()
        bot = self.sudo()._bot_user()
        company = self.sudo().company_id
        if bot:
            return (
                self.with_user(bot)
                .with_company(company)
                .with_context(allowed_company_ids=[company.id])
            )
        # fallback (sem bot): escopo por empresa via sudo
        return self.sudo()._scoped()

    @api.constrains("provider", "evo_instance", "company_id")
    def _check_evo_instance_unique(self):
        for ch in self:
            if ch.provider == "evolution" and ch.evo_instance:
                dup = self.search(
                    [
                        ("id", "!=", ch.id),
                        ("provider", "=", "evolution"),
                        ("evo_instance", "=", ch.evo_instance),
                    ],
                    limit=1,
                )
                if dup:
                    raise ValidationError(
                        _("A instância Evolution '%s' já está em uso por outro canal.")
                        % ch.evo_instance
                    )

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
            allowed_company_ids=[self.company_id.id]
        )

    # ---------- envio ----------
    def send_text(self, number, body):
        self.ensure_one()
        to = _e164_br(number)
        if not to:
            raise UserError(_("Número de WhatsApp inválido."))
        if not body:
            raise UserError(_("Mensagem vazia."))
        # Credenciais do canal são restritas a admin (groups=group_system); o
        # envio roda como usuário técnico (bot) — por isso lê via sudo() aqui.
        channel = self.sudo()
        return {
            "evolution": channel._send_evolution,
            "meta_cloud": channel._send_meta_cloud,
            "twilio": channel._send_twilio,
        }[channel.provider](to, body)

    def _post(self, url, **kwargs):
        try:
            resp = requests.post(url, timeout=_TIMEOUT, **kwargs)
        except requests.exceptions.RequestException as e:
            _logger.warning("DZ23 WhatsApp erro de rede: %s", e)
            raise UserError(_("Falha de rede ao enviar WhatsApp.")) from None
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
        return self._post(
            url, headers={"apikey": self.evo_apikey}, json={"number": to, "text": body}
        )

    def _send_meta_cloud(self, to, body):
        if not (self.meta_token and self.meta_phone_id):
            raise UserError(_("Canal Meta incompleto (token/phone_id)."))
        url = "https://graph.facebook.com/%s/%s/messages" % (
            self.meta_api_version or "v20.0",
            self.meta_phone_id,
        )
        return self._post(
            url,
            headers={"Authorization": "Bearer %s" % self.meta_token},
            json={
                "messaging_product": "whatsapp",
                "to": to,
                "type": "text",
                "text": {"body": body},
            },
        )

    def _send_twilio(self, to, body):
        if not (self.twilio_sid and self.twilio_token and self.twilio_from):
            raise UserError(_("Canal Twilio incompleto (sid/token/from)."))
        url = "https://api.twilio.com/2010-04-01/Accounts/%s/Messages.json" % self.twilio_sid
        frm = (
            self.twilio_from
            if self.twilio_from.startswith("whatsapp:")
            else "whatsapp:%s" % self.twilio_from
        )
        return self._post(
            url,
            data={"From": frm, "To": "whatsapp:+%s" % to, "Body": body},
            auth=(self.twilio_sid, self.twilio_token),
        )

    # ---------- inbound (base: só registra; dz23_agent sobrescreve) ----------
    def handle_inbound(self, number, text, raw=None):
        """Processa uma mensagem recebida NO ESCOPO da empresa do canal.
        Base apenas registra; o módulo dz23_agent sobrescreve para atender."""
        self.ensure_one()
        _logger.info(
            "[canal %s/%s] inbound de %s: %s",
            self.id,
            self.company_id.display_name,
            number,
            (text or "")[:80],
        )
        return False

    # ---------- Evolution: provisionamento por canal ----------
    def _evo_req(self, method, path, **kwargs):
        self.ensure_one()
        if not (self.evo_base and self.evo_apikey):
            raise UserError(_("Configure a base URL e a apikey da Evolution no canal."))
        url = "%s%s" % (self.evo_base.rstrip("/"), path)
        try:
            resp = requests.request(
                method,
                url,
                timeout=_TIMEOUT,
                headers={"apikey": self.evo_apikey, "Content-Type": "application/json"},
                **kwargs,
            )
        except requests.exceptions.RequestException as e:
            raise UserError(_("Não foi possível falar com o servidor Evolution: %s") % e) from e
        try:
            return resp.json()
        except ValueError:
            return {"raw": resp.text}

    def _webhook_url(self, kind):
        # Base ALCANÇÁVEL pelo provedor (rede interna de containers), distinta da
        # web.base.url pública. Configurável em dz23.whatsapp.webhook_base.
        ICP = self.env["ir.config_parameter"].sudo()
        base = (
            ICP.get_param("dz23.whatsapp.webhook_base")
            or ICP.get_param("web.base.url")
            or "http://localhost:8069"
        ).rstrip("/")
        return "%s/dz23/whatsapp/%s/webhook/%s" % (base, kind, self.webhook_token)

    def action_evolution_connect(self):
        """Botão do canal: abre o assistente de QR JÁ VINCULADO A ESTE canal
        (corrige HIGH-1: antes retornava um dict cru e nunca exibia o QR; e o
        caminho de Ajustes conectava o canal padrão, não o que está aberto)."""
        self.ensure_one()
        wiz = self.env["dz23.whatsapp.evolution"].create({"channel_id": self.id})
        wiz._load_qr()
        return {
            "type": "ir.actions.act_window",
            "name": _("Conectar WhatsApp (Evolution)"),
            "res_model": "dz23.whatsapp.evolution",
            "res_id": wiz.id,
            "view_mode": "form",
            "target": "new",
        }

    def _evolution_provision(self):
        """Cria a instância (se preciso), configura o webhook tokenizado e devolve o QR."""
        self.ensure_one()
        if not self.evo_instance:
            self.evo_instance = "dz23_%s_%s" % (self.company_id.id, self.id)
        self._evo_req(
            "POST",
            "/instance/create",
            json={
                "instanceName": self.evo_instance,
                "integration": "WHATSAPP-BAILEYS",
                "qrcode": True,
            },
        )
        # webhook tokenizado + SEGREDO DE CALLBACK próprio no header (independente
        # da chave administrativa). O endpoint é fail-closed e valida esse header.
        self._evo_req(
            "POST",
            "/webhook/set/%s" % self.evo_instance,
            json={
                "webhook": {
                    "enabled": True,
                    "url": self._webhook_url("evolution"),
                    "webhookByEvents": False,
                    "events": ["MESSAGES_UPSERT"],
                    "headers": {
                        "X-DZ23-Callback": self.callback_secret,
                        "Content-Type": "application/json",
                    },
                }
            },
        )
        data = self._evo_req("GET", "/instance/connect/%s" % self.evo_instance)
        qr = data.get("base64") or (data.get("qrcode") or {}).get("base64") or ""
        return {"instance": self.evo_instance, "qr": qr, "webhook": self._webhook_url("evolution")}

    def action_rotate_callback_secret(self):
        """Gera um novo segredo de callback e reconfigura o webhook do provedor."""
        self.ensure_one()
        self.callback_secret = secrets.token_urlsafe(32)
        if self.provider == "evolution" and self.evo_instance:
            self._evo_req(
                "POST",
                "/webhook/set/%s" % self.evo_instance,
                json={
                    "webhook": {
                        "enabled": True,
                        "url": self._webhook_url("evolution"),
                        "webhookByEvents": False,
                        "events": ["MESSAGES_UPSERT"],
                        "headers": {
                            "X-DZ23-Callback": self.callback_secret,
                            "Content-Type": "application/json",
                        },
                    }
                },
            )
        return True
