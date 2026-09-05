/** @odoo-module **/
// Debrand do menu do usuário (canto superior direito):
// - remove "My Odoo.com Account"
// - troca o "Help" (suporte Odoo) por "Ajuda" apontando para o DZ23
// Carrega depois do módulo web, então os itens já estão registrados.

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { browser } from "@web/core/browser/browser";

const userMenu = registry.category("user_menuitems");

// Remover itens com marca Odoo (guardado: só remove se existir)
for (const key of ["odoo_account"]) {
    if (userMenu.contains(key)) {
        userMenu.remove(key);
    }
}

// Repontar o "Help" para o DZ23 (remove o original e adiciona o nosso)
if (userMenu.contains("support")) {
    userMenu.remove("support");
}
userMenu.add("dz23_support", function dz23SupportItem() {
    const url = "https://www.dz23.com.br";
    return {
        type: "item",
        id: "dz23_support",
        description: _t("Ajuda"),
        href: url,
        callback: () => browser.open(url, "_blank"),
        sequence: 20,
    };
});
