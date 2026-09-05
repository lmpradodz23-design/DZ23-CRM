from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    dz23_agent_autoreply = fields.Boolean(
        "Responder WhatsApp automaticamente (IA)",
        config_parameter="dz23.agent.autoreply",
        default=True,
    )
    dz23_agent_prompt = fields.Text(
        "Instruções do atendente (IA)",
        config_parameter="dz23.agent.prompt",
    )
