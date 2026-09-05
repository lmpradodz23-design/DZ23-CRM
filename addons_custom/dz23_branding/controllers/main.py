# -*- coding: utf-8 -*-
# Rebrand do PWA (manifest): nome, cores e ícones DZ23 CRM.
# Estende o controller nativo web.WebManifest sem editar o core.
from odoo.addons.web.controllers.webmanifest import WebManifest

DZ23_NAVY = "#003175"


class DZ23WebManifest(WebManifest):

    def _get_webmanifest(self):
        manifest = super()._get_webmanifest()
        # Nome do app (também controlado por ir.config_parameter web.web_app_name)
        manifest["name"] = "DZ23 CRM"
        manifest["short_name"] = "DZ23 CRM"
        # Cores da marca (Odoo usa #714B67 roxo por padrão)
        manifest["background_color"] = DZ23_NAVY
        manifest["theme_color"] = DZ23_NAVY
        # Ícones DZ23 servidos pelo próprio módulo
        manifest["icons"] = [
            {
                "src": "/dz23_branding/static/src/img/icon-192.png",
                "sizes": "192x192",
                "type": "image/png",
            },
            {
                "src": "/dz23_branding/static/src/img/icon-512.png",
                "sizes": "512x512",
                "type": "image/png",
            },
        ]
        return manifest
