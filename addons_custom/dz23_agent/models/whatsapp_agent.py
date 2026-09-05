# -*- coding: utf-8 -*-
# Cérebro do atendente/vendedor: recebe WhatsApp -> entende a intenção ->
#   agenda (cria evento na Agenda, que sincroniza com o Google Calendar),
#   vende (abre orçamento/pedido com base no catálogo do negócio),
#   ou responde com IA usando o contexto REAL da empresa (qualquer ramo).
# Estende o serviço dz23.whatsapp (funciona tanto p/ Meta quanto Evolution).
import logging
import re
from datetime import timedelta

from odoo import fields, models
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)

_DEFAULT_PROMPT = (
    "Você é o atendente e vendedor virtual desta empresa. Atenda com cordialidade e "
    "objetividade, em português do Brasil. Seu papel é entender o que o cliente precisa, "
    "informar produtos/serviços e preços com base no catálogo, tirar dúvidas, ajudar a "
    "fechar a venda e, quando fizer sentido, marcar um horário. Sirva qualquer ramo "
    "(salão, loja, clínica, oficina, serviços, etc.) — use SEMPRE o contexto da empresa abaixo."
)
_SCHED_RE = re.compile(r"agend|marc|hor[aá]rio|reuni|consulta|atend|hor[aá]rios", re.IGNORECASE)
_BUY_RE = re.compile(
    r"compr|pre[çc]o|valor|quanto\s+custa|or[çc]amento|pedido|adquirir|contratar|"
    r"quero\s+(?:o|a|um|uma|comprar)|me\s+v[eê]nd", re.IGNORECASE)


def _digits(v):
    return re.sub(r"\D", "", v or "")


def _strip_html(v):
    return re.sub(r"<[^>]+>", " ", v or "").strip()


class DZ23WhatsAppAgent(models.AbstractModel):
    _inherit = "dz23.whatsapp"

    # ---- flags / util -----------------------------------------------------
    def _agent_enabled(self):
        return (self._param("dz23.agent.autoreply", "1") or "1") not in ("0", "False", "false")

    def _agent_find_lead(self, number):
        """Acha ou cria um lead do CRM pelo telefone (liga WhatsApp -> CRM)."""
        digits = _digits(number)
        tail = digits[-8:] if len(digits) >= 8 else digits
        Lead = self.env["crm.lead"]
        lead = Lead.search([("phone", "ilike", tail)], limit=1) if tail else Lead
        if lead:
            return lead
        Partner = self.env["res.partner"]
        partner = Partner.search([("phone", "ilike", tail)], limit=1) if tail else Partner
        return Lead.create({
            "name": _("WhatsApp %s") % number,
            "phone": number,
            "type": "lead",
            "partner_id": partner.id if partner else False,
        })

    def _agent_partner_for(self, lead):
        """Garante um contato (res.partner) para o lead — necessário p/ orçamento."""
        if lead.partner_id:
            return lead.partner_id
        partner = self.env["res.partner"].create({
            "name": lead.contact_name or lead.name or _("Cliente WhatsApp"),
            "phone": lead.phone or "",
        })
        lead.partner_id = partner.id
        return partner

    # ---- contexto do negócio (torna o robô genérico p/ qualquer ramo) -----
    def _agent_catalog(self, limit=40):
        """Lista produtos/serviços vendáveis do negócio (recordset)."""
        return self.env["product.template"].search(
            [("sale_ok", "=", True)], order="list_price desc", limit=limit)

    def _agent_business_context(self):
        """Texto com empresa + catálogo, injetado na IA para ela vender em qualquer ramo."""
        company = self.env.company
        parts = [_("Empresa: %s.") % (company.name or "DZ23 CRM")]
        currency = company.currency_id.symbol or "R$"
        prods = self._agent_catalog()
        if prods:
            cat = [u"- %s: %s %.2f" % (p.name, currency, p.list_price or 0.0) for p in prods]
            parts.append(_("Catálogo de produtos/serviços à venda:\n%s") % "\n".join(cat))
        else:
            parts.append(_(
                "Ainda não há produtos cadastrados no sistema; faça o atendimento, "
                "entenda a necessidade do cliente e colete os dados do interesse."))
        return "\n".join(parts)

    def _agent_history(self, lead, limit=6):
        """Últimas mensagens do chatter do lead — dá memória de conversa ao robô."""
        msgs = self.env["mail.message"].search(
            [("model", "=", lead._name), ("res_id", "=", lead.id)],
            order="id desc", limit=limit)
        hist = []
        for msg in reversed(msgs):
            body = _strip_html(msg.body)
            if body:
                hist.append(body)
        return "\n".join(hist[-limit:])

    def _agent_system_prompt(self, lead):
        base = self._param("dz23.agent.prompt") or _DEFAULT_PROMPT
        history = self._agent_history(lead)
        blocks = [base, self._agent_business_context()]
        if history:
            blocks.append(_("Histórico recente da conversa:\n%s") % history)
        return "\n\n".join(blocks)

    # ---- detecção de intenção --------------------------------------------
    def _agent_parse_datetime(self, text):
        """Extrai data/hora de textos tipo '10/09 às 14:30'. Retorna datetime ou False."""
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
        """Casa o texto do cliente com um produto/serviço do catálogo (ou False)."""
        t = (text or "").lower()
        for p in self._agent_catalog():
            name = (p.name or "").lower().strip()
            if len(name) >= 3 and name in t:
                return p
        return False

    # ---- ações ------------------------------------------------------------
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
        """Abre um orçamento (sale.order em rascunho) — venda real, reversível, sem cobrar."""
        if "sale.order" not in self.env:
            return False
        partner = self._agent_partner_for(lead)
        variant = product.product_variant_id
        so = self.env["sale.order"].create({
            "partner_id": partner.id,
            "origin": "WhatsApp DZ23",
            "order_line": [(0, 0, {
                "product_id": variant.id,
                "product_uom_qty": 1.0,
            })],
        })
        lead.message_post(body=_("🛒 Orçamento %s aberto: %s") % (so.name, product.name))
        return so

    # ---- pipeline principal ----------------------------------------------
    def _agent_reply_ai(self, lead, text, fallback):
        try:
            return self.env["dz23.ai"].chat(text, system=self._agent_system_prompt(lead))
        except Exception as e:  # noqa: BLE001 - IA pode não estar configurada
            _logger.info("Agente: IA indisponível (%s), usando resposta padrão.", type(e).__name__)
            return fallback

    def _on_inbound(self, number, text, raw=None):
        if not self._agent_enabled():
            return super()._on_inbound(number, text, raw)

        lead = self._agent_find_lead(number)
        lead.message_post(body=_("📩 WhatsApp recebido de %s: %s") % (number, text))

        # 1) Agendamento em tempo real (cria evento -> Google Calendar).
        when = self._agent_parse_datetime(text) if _SCHED_RE.search(text or "") else False
        if when:
            self._agent_create_event(lead, when)
            reply = _("Perfeito! Agendei para %s. Se precisar remarcar, é só falar. 💙 DZ23") % (
                when.strftime("%d/%m/%Y às %H:%M"))
        else:
            # 2) Venda: intenção de compra + produto do catálogo -> abre orçamento.
            product = self._agent_match_product(text) if _BUY_RE.search(text or "") else False
            quote = self._agent_create_quote(lead, product) if product else False
            if quote:
                fallback = _(
                    "Boa escolha! Anotei seu pedido de %s (%s %.2f). "
                    "Posso confirmar para você fechar? 💙 DZ23") % (
                    product.name, self.env.company.currency_id.symbol or "R$",
                    product.list_price or 0.0)
            else:
                fallback = _("Recebemos sua mensagem e já retornamos. 💙 DZ23 CRM")
            # 3) IA responde com o contexto do negócio (vende/atende qualquer ramo).
            reply = self._agent_reply_ai(lead, text, fallback)

        try:
            self.send_text(number, reply)
            lead.message_post(body=_("🤖 Resposta enviada: %s") % reply)
        except Exception as e:  # noqa: BLE001 - envio pode falhar sem provedor
            lead.message_post(body=_("⚠️ Resposta gerada mas não enviada agora (%s): %s")
                              % (type(e).__name__, reply))
        return True
