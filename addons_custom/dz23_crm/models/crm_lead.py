import re

from odoo import api, fields, models


def _only_digits(value):
    return re.sub(r"\D", "", value or "")


class CrmLead(models.Model):
    _inherit = "crm.lead"

    dz23_whatsapp_link = fields.Char(
        "Link WhatsApp", compute="_compute_dz23_whatsapp_link", store=False
    )

    def action_dz23_send_whatsapp(self):
        """Abre o assistente de envio de WhatsApp já com o telefone do lead."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Enviar WhatsApp",
            "res_model": "dz23.whatsapp.compose",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_number": self.phone or "",
                "default_res_model": "crm.lead",
                "default_res_id": self.id,
            },
        }

    @api.depends("phone")
    def _compute_dz23_whatsapp_link(self):
        for lead in self:
            raw = _only_digits(lead.phone or "")
            link = False
            if raw:
                if not raw.startswith("55") and len(raw) in (10, 11):
                    raw = "55" + raw
                if 12 <= len(raw) <= 13:
                    link = "https://wa.me/%s" % raw
            lead.dz23_whatsapp_link = link
