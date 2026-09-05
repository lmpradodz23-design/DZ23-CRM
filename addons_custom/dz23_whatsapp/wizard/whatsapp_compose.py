# -*- coding: utf-8 -*-
from odoo import fields, models
from odoo.tools.translate import _


class DZ23WhatsAppCompose(models.TransientModel):
    _name = "dz23.whatsapp.compose"
    _description = "DZ23 — Enviar WhatsApp"

    number = fields.Char("Número (WhatsApp)", required=True)
    body = fields.Text("Mensagem", required=True)
    res_model = fields.Char()
    res_id = fields.Integer()

    def action_send(self):
        self.ensure_one()
        # Usa o serviço plugável (Meta/Twilio/Evolution). Erra com mensagem clara se não configurado.
        self.env["dz23.whatsapp"].send_text(self.number, self.body)
        # Registra no chatter do registro de origem (lead/contato), se houver.
        if self.res_model and self.res_id and self.res_model in self.env.registry:
            rec = self.env[self.res_model].browse(self.res_id)
            if rec.exists() and hasattr(rec, "message_post"):
                rec.message_post(body=_("WhatsApp enviado para %s:<br/>%s") % (self.number, self.body))
        return {"type": "ir.actions.act_window_close"}
