from odoo import fields, models
from odoo.tools.translate import _


class DZ23EvolutionConnect(models.TransientModel):
    _name = "dz23.whatsapp.evolution"
    _description = "DZ23 — Conectar WhatsApp (Evolution / QR)"

    channel_id = fields.Many2one("dz23.channel", string="Canal", readonly=True)
    instance = fields.Char("Instância", readonly=True)
    webhook = fields.Char("Webhook configurado", readonly=True)
    qr_image = fields.Binary("QR Code", readonly=True)
    info = fields.Char(readonly=True)

    def _load_qr(self):
        # Usa o canal vinculado (botão do canal); só cai no canal padrão da
        # empresa quando aberto sem canal (ex.: atalho de Ajustes).
        channel = self.channel_id or self.env["dz23.whatsapp"]._default_channel()
        if not channel:
            self.info = _("Crie um Canal de WhatsApp primeiro (menu DZ23 WhatsApp).")
            return
        res = channel._evolution_provision()  # cria instância + webhook + QR
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
