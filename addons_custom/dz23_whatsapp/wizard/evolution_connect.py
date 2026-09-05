from odoo import fields, models
from odoo.tools.translate import _


class DZ23EvolutionConnect(models.TransientModel):
    _name = "dz23.whatsapp.evolution"
    _description = "DZ23 — Conectar WhatsApp (Evolution / QR)"

    instance = fields.Char("Instância", readonly=True)
    webhook = fields.Char("Webhook configurado", readonly=True)
    qr_image = fields.Binary("QR Code", readonly=True)
    info = fields.Char(readonly=True)

    def _load_qr(self):
        res = self.env["dz23.whatsapp"].evolution_connect()  # cria instância + webhook + QR
        qr = res.get("qr") or ""
        if qr.startswith("data:"):
            qr = qr.split(",", 1)[-1]
        self.write(
            {
                "instance": res.get("instance"),
                "webhook": res.get("webhook"),
                "qr_image": qr or False,
                "info": _(
                    "Abra o WhatsApp no celular > Aparelhos conectados > Conectar aparelho e escaneie o QR."
                )
                if qr
                else _(
                    "A instância pode já estar conectada (sem QR). Verifique no painel Evolution."
                ),
            }
        )

    def action_refresh(self):
        self.ensure_one()
        self._load_qr()
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }
