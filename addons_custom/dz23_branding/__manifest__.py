# DZ23 CRM — módulo de rebrand/debrand sobre Odoo 19 Community (LGPLv3).
# Este módulo NÃO edita o core do Odoo: ele herda/sobrescreve templates e
# registros para trocar a marca "Odoo" pela marca "DZ23 CRM".
{
    "name": "DZ23 CRM — Branding",
    "version": "19.0.1.0.0",
    "summary": "Rebrand completo (debrand) do Odoo para DZ23 CRM.",
    "author": "DZ23 (LEANDRO MARCOS PRADO LTDA)",
    "website": "https://www.dz23.com.br",
    # Obra derivada do Odoo (LGPLv3). A licença da base é mantida.
    "license": "MIT",
    "category": "Tools",
    "depends": ["web", "mail", "portal"],
    "data": [
        "data/branding_data.xml",
        "views/webclient_templates.xml",
        "views/mail_layout.xml",
        "views/portal_templates.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "dz23_branding/static/src/js/user_menu_debrand.js",
            "dz23_branding/static/src/js/title_service_patch.js",
            "dz23_branding/static/src/scss/branding.scss",
        ],
    },
    "installable": True,
    "application": False,
    # Ativa pt-BR como idioma padrão ao instalar.
    "post_init_hook": "post_init_hook",
}
