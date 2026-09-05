# -*- coding: utf-8 -*-
# DZ23 CRM — integrações gratuitas Brasil (BrasilAPI/OSM): autofill CNPJ/CEP,
# enriquecimento de lead, feriados, câmbio e botão WhatsApp (wa.me).
{
    "name": "DZ23 CRM — Ferramentas Brasil",
    "version": "19.0.1.0.0",
    "summary": "Autofill CNPJ/CEP, enriquecimento de lead, feriados e WhatsApp (wa.me) — APIs gratuitas.",
    "author": "DZ23 (LEANDRO MARCOS PRADO LTDA)",
    "website": "https://www.dz23.com.br",
    "license": "LGPL-3",
    "category": "Sales/CRM",
    "depends": ["contacts", "phone_validation"],
    "data": [
        "data/config_params.xml",
        "views/res_partner_views.xml",
    ],
    "installable": True,
    "application": False,
}
