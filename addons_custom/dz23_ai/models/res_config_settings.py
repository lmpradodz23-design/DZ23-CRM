from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    dz23_ai_provider = fields.Selection(
        selection=[
            ("ollama", "Local grátis (Ollama) — sem custo de token"),
            ("groq", "Groq (free-tier)"),
            ("google", "Google Gemini (free-tier)"),
            ("openai", "OpenAI (pago)"),
            ("anthropic", "Anthropic (pago)"),
        ],
        string="Provedor de IA",
        default="ollama",
        config_parameter="dz23.ai_provider",
    )
    dz23_ai_model = fields.Char(
        "Modelo",
        help="Ex.: llama3.1 (Ollama), llama-3.3-70b-versatile (Groq), gpt-4o-mini…",
        config_parameter="dz23.ai_model",
    )
    dz23_ai_ollama_base = fields.Char(
        "Ollama base URL (local, grátis)",
        default="http://host.docker.internal:11434",
        config_parameter="dz23.ai.ollama_base",
    )
    dz23_ai_groq_key = fields.Char("Groq API key", config_parameter="dz23.ai.groq_key")
    dz23_ai_google_key = fields.Char(
        "Google (Gemini) API key", config_parameter="dz23.ai.google_key"
    )
    dz23_ai_openai_key = fields.Char("OpenAI API key", config_parameter="dz23.ai.openai_key")
    dz23_ai_anthropic_key = fields.Char(
        "Anthropic API key", config_parameter="dz23.ai.anthropic_key"
    )
