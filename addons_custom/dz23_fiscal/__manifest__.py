# DZ23 CRM — Fiscal (NF-e) via provedor de terceiros.
# Módulo OPCIONAL (não faz parte do MVP CRM enxuto): instala a estrutura para
# emitir NF-e chamando a API de um provedor (Focus NFe / NFe.io / Nuvem Fiscal).
# A emissão real depende de certificado e-CNPJ A1 + conta do provedor +
# validação contábil => BLOCKED_BY_EXTERNAL_DEPENDENCY até fornecidos.
{
    "name": "DZ23 CRM — Fiscal NF-e (provedor)",
    "version": "19.0.1.0.0",
    "summary": "Emissão de NF-e via API de provedor (estrutura; emissão requer certificado+conta).",
    "author": "DZ23 (LEANDRO MARCOS PRADO LTDA)",
    "website": "https://www.dz23.com.br",
    "license": "LGPL-3",
    "category": "Accounting",
    "depends": ["account"],
    "data": [
        "data/config_params.xml",
        "views/account_move_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "installable": True,
    "application": False,
}
