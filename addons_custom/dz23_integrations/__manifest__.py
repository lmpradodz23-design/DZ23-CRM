# DZ23 CRM — Hub de Integrações: cards com status, logo e link para cadastrar/
# ativar cada API (fiscal, comunicação, pagamento, IA, marketplace).
{
    "name": "DZ23 CRM — Integrações",
    "version": "19.0.1.0.0",
    "summary": "Central de integrações: cadastrar e ativar APIs (fiscal, comunicação, pagamento, IA, marketplace).",
    "author": "DZ23 (LEANDRO MARCOS PRADO LTDA)",
    "website": "https://www.dz23.com.br",
    "license": "LGPL-3",
    "category": "Tools",
    "depends": ["base_setup", "mail"],
    "data": [
        "security/ir.model.access.csv",
        "views/integration_views.xml",
        "data/integrations_data.xml",
    ],
    "installable": True,
    "application": True,
    "post_init_hook": "post_init_hook",
}
