# -*- coding: utf-8 -*-
# DZ23 CRM — WhatsApp plugável (adaptador por provedor).
# Provedores: Meta WhatsApp Cloud API, Twilio, Evolution API.
# Credenciais ficam em ir.config_parameter (servidor), NUNCA no código.
{
    "name": "DZ23 CRM — WhatsApp",
    "version": "19.0.1.0.0",
    "summary": "Envio de WhatsApp plugável (Meta Cloud API / Twilio / Evolution).",
    "author": "DZ23 (LEANDRO MARCOS PRADO LTDA)",
    "website": "https://www.dz23.com.br",
    "license": "LGPL-3",
    "category": "Marketing",
    "depends": ["mail", "phone_validation"],
    "data": [
        "security/ir.model.access.csv",
        "data/config_params.xml",
        "views/res_config_settings_views.xml",
        "wizard/whatsapp_compose_views.xml",
    ],
    "installable": True,
    "application": False,
}
