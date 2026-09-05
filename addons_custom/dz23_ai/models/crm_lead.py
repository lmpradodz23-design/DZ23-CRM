# -*- coding: utf-8 -*-
from odoo import models
from odoo.tools.translate import _


class CrmLead(models.Model):
    _inherit = "crm.lead"

    def action_dz23_ai_summary(self):
        """Resume o lead com IA e registra no chatter."""
        self.ensure_one()
        prompt = _(
            "Resuma este lead de vendas em português, com próximos passos objetivos:\n"
            "Nome: %s\nEmpresa: %s\nE-mail: %s\nTelefone: %s\nDescrição: %s"
        ) % (
            self.contact_name or self.name or "",
            self.partner_name or "",
            self.email_from or "",
            self.phone or "",
            self.description or "",
        )
        text = self.env["dz23.ai"].chat(
            prompt, system=_("Você é um assistente de vendas do DZ23 CRM.")
        )
        self.message_post(body=text or _("(sem resposta da IA)"))
        return True
