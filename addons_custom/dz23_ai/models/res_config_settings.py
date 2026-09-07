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
    # Gate de privacidade (LGPD): provedores EXTERNOS (Groq/OpenAI/Gemini/
    # Anthropic) só são usados se este consentimento estiver ligado. Local
    # (Ollama) nunca é bloqueado. Sem isto, escolher um provedor externo não
    # funciona — por segurança/privacidade dos dados dos clientes (HIGH-2).
    dz23_ai_external_allowed = fields.Boolean(
        "Permitir enviar dados a IA EXTERNA (consentimento/LGPD)",
        help="Ao ligar, você confirma ter base legal para enviar dados (com PII "
        "redigida) a provedores externos. Deixe desligado para usar só IA local.",
        config_parameter="dz23.ai.external_allowed",
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
