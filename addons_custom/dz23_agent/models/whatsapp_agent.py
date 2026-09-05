# -*- coding: utf-8 -*-
# Cérebro do atendente: recebe WhatsApp -> IA responde -> envia de volta;
# se detectar intenção de horário, cria evento na Agenda e confirma.
# Estende o serviço dz23.whatsapp (funciona tanto p/ Meta quanto Evolution).
import logging
import re
from datetime import timedelta

from odoo import fields, models
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)

_DEFAULT_PROMPT = (
    "Você é o atendente virtual do DZ23 CRM. Responda em português do Brasil, "
    "cordial e objetivo. Se o cliente quiser marcar algo, peça data e horário."
)
_SCHED_RE = re.compile(r"agend|marc|hor[aá]rio|reuni|consulta|atend", re.IGNORECASE)


def _digits(v):
    return re.sub(r"\D", "", v or "")


class DZ23WhatsAppAgent(models.AbstractModel):
    _inherit = "dz23.whatsapp"

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

    def _on_inbound(self, number, text, raw=None):
        if not self._agent_enabled():
            return super()._on_inbound(number, text, raw)

        lead = self._agent_find_lead(number)
        lead.message_post(body=_("📩 WhatsApp recebido de %s: %s") % (number, text))

        when = self._agent_parse_datetime(text) if _SCHED_RE.search(text or "") else False
        if when:
            self.env["calendar.event"].create({
                "name": _("Agendamento WhatsApp — %s") % (lead.contact_name or lead.name),
                "start": fields.Datetime.to_string(when),
                "stop": fields.Datetime.to_string(when + timedelta(hours=1)),
                "partner_ids": [(4, lead.partner_id.id)] if lead.partner_id else [],
                "opportunity_id": lead.id if lead._name == "crm.lead" else False,
            })
            reply = _("Perfeito! Agendei para %s. Se precisar remarcar, é só falar. 💙 DZ23") % (
                when.strftime("%d/%m/%Y às %H:%M"))
            lead.message_post(body=_("📅 Evento criado para %s") % when.strftime("%d/%m/%Y %H:%M"))
        else:
            try:
                reply = self.env["dz23.ai"].chat(
                    text, system=self._param("dz23.agent.prompt") or _DEFAULT_PROMPT)
            except Exception as e:  # noqa: BLE001 - IA pode não estar configurada
                _logger.info("Agente: IA indisponível (%s), usando resposta padrão.", type(e).__name__)
                reply = _("Recebemos sua mensagem e já retornamos. 💙 DZ23 CRM")

        try:
            self.send_text(number, reply)
            lead.message_post(body=_("🤖 Resposta enviada: %s") % reply)
        except Exception as e:  # noqa: BLE001 - envio pode falhar sem provedor
            lead.message_post(body=_("⚠️ Resposta gerada mas não enviada agora (%s): %s")
                              % (type(e).__name__, reply))
        return True
