/** @odoo-module **/
// Título da aba do navegador: o Odoo usa a parte "zopenerp" = "Odoo" como
// sufixo. Trocamos por "DZ23 CRM". Serviço não-intrusivo e defensivo:
// se a API do serviço de título mudar, o try/catch evita quebrar o webclient.

import { registry } from "@web/core/registry";

const dz23TitleService = {
    dependencies: ["title"],
    start(env, { title }) {
        try {
            title.setParts({ zopenerp: "DZ23 CRM" });
        } catch {
            // API do serviço de título diferente nesta versão — ignora com segurança.
        }
    },
};

registry.category("services").add("dz23_title", dz23TitleService);
