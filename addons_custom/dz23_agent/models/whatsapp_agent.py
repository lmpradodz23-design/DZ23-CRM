# -*- coding: utf-8 -*-
# Cérebro do atendente/vendedor, agora POR CANAL e no ESCOPO da empresa do canal
# (multi-tenant). Estende dz23.channel e sobrescreve handle_inbound:
#   - agenda (cria evento -> Google Calendar),
#   - vende (abre orçamento na empresa do canal),
#   - ou responde com IA usando o catálogo/persona daquela empresa.
# A busca de lead é ESCOPADA por empresa (nunca global por cauda de telefone).
import logging
import re
from datetime import timedelta

from odoo import fields, models
from odoo.tools.translate import _

from odoo.addons.dz23_whatsapp.models.whatsapp_channel import _digits, _e164_br

_logger = logging.getLogger(__name__)

_DEFAULT_PROMPT = (
    "Você é a Sofia, atendente da equipe (uma pessoa de verdade do atendimento), "
    "conversando pelo WhatsApp. Fale como gente: calorosa, simpática, natural e "
    "direta, em português do Brasil, com no máximo 2 ou 3 frases curtas por mensagem. "
    "Pode usar no máximo 1 emoji quando combinar. "
    "NUNCA diga que é uma inteligência artificial, robô, modelo de linguagem ou "
    "assistente virtual, e nunca peça desculpas por 'não ter informação em tempo real': "
    "você é do time e resolve. Seu papel é entender o que a pessoa precisa, apresentar "
    "produtos/serviços e preços com base no catálogo abaixo, tirar dúvidas, ajudar a "
    "fechar a venda e marcar horário quando fizer sentido. Se não souber um detalhe, diga "
    "que vai confirmar e conduza a conversa com uma pergunta. Atenda qualquer ramo "
    "(salão, loja, clínica, oficina, serviços) usando SEMPRE o contexto da empresa abaixo. "
    "Não invente itens ou preços que não estejam no catálogo."
)
_SCHED_RE = re.compile(r"agend|marc|hor[aá]rio|reuni|consulta|atend|hor[aá]rios", re.IGNORECASE)
_BUY_RE = re.compile(
    r"compr|pre[çc]o|valor|quanto\s+custa|or[çc]amento|pedido|adquirir|contratar|"
    r"quero\s+(?:o|a|um|uma|comprar)|me\s+v[eê]nd", re.IGNORECASE)


def _strip_html(v):
    return re.sub(r"<[^>]+>", " ", v or "").strip()


class DZ23ChannelAgent(models.Model):
    _inherit = "dz23.channel"

    # ---- lead escopado por empresa (nunca busca global) -------------------
    def _agent_find_lead(self, number):
        self.ensure_one()
        e164 = _e164_br(number)
        tail = e164[-11:] if len(e164) >= 11 else e164
        company = self.company_id
        Lead = self.env["crm.lead"]
        dom = [("company_id", "in", (False, company.id))]
        lead = Lead.search(dom + [("phone", "ilike", tail)], limit=1) if tail else Lead.browse()
        if lead:
            return lead
        Partner = self.env["res.partner"]
        partner = Partner.search(
            [("company_id", "in", (False, company.id)), ("phone", "ilike", tail)], limit=1
        ) if tail else Partner.browse()
        return Lead.create({
            "name": _("WhatsApp %s") % number,
            "phone": e164 or number,
            "type": "lead",
            "company_id": company.id,
            "partner_id": partner.id if partner else False,
        })

    def _agent_partner_for(self, lead):
        if lead.partner_id:
            return lead.partner_id
        partner = self.env["res.partner"].create({
            "name": lead.contact_name or lead.name or _("Cliente WhatsApp"),
            "phone": lead.phone or "",
            "company_id": self.company_id.id,
        })
        lead.partner_id = partner.id
        return partner

    # ---- contexto do negócio (escopado por empresa) -----------------------
    def _agent_catalog(self, limit=40):
        return self.env["product.template"].search(
            [("sale_ok", "=", True), ("company_id", "in", (False, self.company_id.id))],
            order="list_price desc", limit=limit)

    def _agent_business_context(self):
        company = self.company_id
        parts = [_("Empresa: %s.") % (company.name or "DZ23 CRM")]
        currency = company.currency_id.symbol or "R$"
        prods = self._agent_catalog()
        if prods:
            cat = [u"- %s: %s %.2f" % (p.name, currency, p.list_price or 0.0) for p in prods]
            parts.append(_("Catálogo de produtos/serviços à venda:\n%s") % "\n".join(cat))
        else:
            parts.append(_(
                "Ainda não há produtos cadastrados; faça o atendimento, entenda a "
                "necessidade do cliente e colete os dados do interesse."))
        return "\n".join(parts)

    def _agent_history(self, lead, limit=6):
        msgs = self.env["mail.message"].search(
            [("model", "=", lead._name), ("res_id", "=", lead.id)],
            order="id desc", limit=limit)
        hist = [b for b in (_strip_html(m.body) for m in reversed(msgs)) if b]
        return "\n".join(hist[-limit:])

    def _agent_system_prompt(self, lead):
        base = self.agent_prompt or _DEFAULT_PROMPT
        blocks = [base, self._agent_business_context()]
        history = self._agent_history(lead)
        if history:
            blocks.append(_("Histórico recente da conversa:\n%s") % history)
        return "\n\n".join(blocks)

    # ---- detecção de intenção --------------------------------------------
    def _agent_parse_datetime(self, text):
        m = re.search(r"(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?(?:\D{0,8}(\d{1,2})(?::(\d{2}))?)?", text or "")
        if not m:
            return False
        import datetime as dt
        now = fields.Datetime.now()
        day, month = int(m.group(1)), int(m.group(2))
        year = int(m.group(3)) if m.group(3) else now.year
        if year < 100:
            year += 2000
        hour = int(m.group(4)) if m.group(4) else 9
        minute = int(m.group(5)) if m.group(5) else 0
        try:
            return dt.datetime(year, month, day, hour, minute)
        except ValueError:
            return False

    def _agent_match_product(self, text):
        t = (text or "").lower()
        for p in self._agent_catalog():
            name = (p.name or "").lower().strip()
            if len(name) >= 3 and name in t:
                return p
        return False

    # ---- ações (na empresa do canal) -------------------------------------
    def _agent_create_event(self, lead, when):
        self.env["calendar.event"].create({
            "name": _("Agendamento WhatsApp — %s") % (lead.contact_name or lead.name),
            "start": fields.Datetime.to_string(when),
            "stop": fields.Datetime.to_string(when + timedelta(hours=1)),
            "partner_ids": [(4, lead.partner_id.id)] if lead.partner_id else [],
            "opportunity_id": lead.id if lead._name == "crm.lead" else False,
        })
        lead.message_post(body=_("📅 Evento criado para %s (sincroniza com Google Calendar)")
                          % when.strftime("%d/%m/%Y %H:%M"))

    def _agent_create_quote(self, lead, product):
        if "sale.order" not in self.env:
            return False
        partner = self._agent_partner_for(lead)
        so = self.env["sale.order"].create({
            "partner_id": partner.id,
            "company_id": self.company_id.id,
            "origin": "WhatsApp DZ23",
            "order_line": [(0, 0, {"product_id": product.product_variant_id.id,
                                   "product_uom_qty": 1.0})],
        })
        lead.message_post(body=_("🛒 Orçamento %s aberto: %s") % (so.name, product.name))
        return so

    def _agent_reply_ai(self, lead, text, fallback):
        try:
            return self.env["dz23.ai"].chat(text, system=self._agent_system_prompt(lead))
        except Exception as e:  # noqa: BLE001 - IA pode não estar configurada
            _logger.info("Agente: IA indisponível (%s), usando resposta padrão.", type(e).__name__)
            return fallback

    # ---- pipeline principal (sobrescreve o gancho do canal) ---------------
    def handle_inbound(self, number, text, raw=None):
        self.ensure_one()
        if not self.agent_autoreply:
            return super().handle_inbound(number, text, raw)

        lead = self._agent_find_lead(number)
        lead.message_post(body=_("📩 WhatsApp recebido de %s: %s") % (number, text))

        when = self._agent_parse_datetime(text) if _SCHED_RE.search(text or "") else False
        if when:
            self._agent_create_event(lead, when)
            reply = _("Perfeito! Agendei para %s. Se precisar remarcar, é só falar. 💙 DZ23") % (
                when.strftime("%d/%m/%Y às %H:%M"))
        else:
            product = self._agent_match_product(text) if _BUY_RE.search(text or "") else False
            quote = self._agent_create_quote(lead, product) if product else False
            if quote:
                fallback = _(
                    "Boa escolha! Anotei seu pedido de %s (%s %.2f). "
                    "Posso confirmar para você fechar? 💙 DZ23") % (
                    product.name, self.company_id.currency_id.symbol or "R$",
                    product.list_price or 0.0)
            else:
                fallback = _(
                    "Oi! Já vi sua mensagem por aqui 😊 Me conta rapidinho o que você "
                    "precisa que eu te ajudo agora mesmo.")
            reply = self._agent_reply_ai(lead, text, fallback)

        try:
            self.send_text(number, reply)
            lead.message_post(body=_("🤖 Resposta enviada: %s") % reply)
        except Exception as e:  # noqa: BLE001 - envio pode falhar sem provedor
            lead.message_post(body=_("⚠️ Resposta gerada mas não enviada agora (%s): %s")
                              % (type(e).__name__, reply))
        return True
