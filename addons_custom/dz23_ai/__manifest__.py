# DZ23 CRM — IA integrada (texto + visão), com opção GRÁTIS/local (Ollama)
# e provedores free-tier/pagos. Chaves ficam em Ajustes (servidor), nunca no código.
{
    "name": "DZ23 CRM — IA",
    "version": "19.0.1.0.0",
    "summary": "IA integrada: local grátis (Ollama), Groq/Gemini (free-tier), OpenAI/Anthropic. Texto e visão.",
    "author": "DZ23 (LEANDRO MARCOS PRADO LTDA)",
    "website": "https://www.dz23.com.br",
    "license": "LGPL-3",
    "category": "Productivity",
    "depends": ["base", "mail", "crm"],
    "data": [
        "data/config_params.xml",
        "views/res_config_settings_views.xml",
        "views/crm_lead_views.xml",
    ],
    "installable": True,
    "application": False,
}
