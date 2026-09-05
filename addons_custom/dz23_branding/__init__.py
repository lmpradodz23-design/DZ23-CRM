# -*- coding: utf-8 -*-
from . import controllers


def post_init_hook(env):
    """Ativa o Português do Brasil e o define como idioma padrão do DZ23 CRM.

    Defensivo: se a API mudar, registra no log e não interrompe a instalação.
    """
    import logging
    _logger = logging.getLogger(__name__)
    lang_code = "pt_BR"
    try:
        # Ativa o idioma (carrega as traduções pt_BR já incluídas no Odoo)
        env["res.lang"]._activate_lang(lang_code)
        # Novos parceiros/usuários nascem em pt_BR
        env["ir.default"].set("res.partner", "lang", lang_code)
        # Usuários internos existentes passam a ver a UI em pt_BR
        users = env["res.users"].search([("share", "=", False)])
        if users:
            users.write({"lang": lang_code})
        _logger.info("DZ23 branding: idioma padrão definido para %s", lang_code)
    except Exception as e:  # noqa: BLE001 - não pode quebrar a instalação
        _logger.warning("DZ23 branding: falha ao ativar %s: %s", lang_code, e)
    try:
        # Renomeia o bot do sistema "OdooBot" -> "DZ23 Bot".
        root = env.ref("base.partner_root", raise_if_not_found=False)
        if root and root.name != "DZ23 Bot":
            root.sudo().write({"name": "DZ23 Bot"})
            _logger.info("DZ23 branding: bot do sistema renomeado para DZ23 Bot")
        # Desliga o tour do robô (popup intrusivo + textos com "Odoo")
        users = env["res.users"].with_context(active_test=False).search([])
        if users and "odoobot_state" in env["res.users"]._fields:
            users.write({"odoobot_state": "disabled"})
    except Exception as e:  # noqa: BLE001
        _logger.warning("DZ23 branding: falha no rename do bot: %s", e)
    try:
        # Dados da empresa + branding do site público (e-commerce), se instalado.
        company = env.ref("base.main_company", raise_if_not_found=False)
        if company:
            vals = {}
            if not company.phone:
                vals["phone"] = "+55 61 98100-3000"
            br = env.ref("base.br", raise_if_not_found=False)
            if br:
                vals["country_id"] = br.id
            brl = env["res.currency"].with_context(active_test=False).search(
                [("name", "=", "BRL")], limit=1)
            if brl:
                if not brl.active:
                    brl.sudo().write({"active": True})
                vals["currency_id"] = brl.id
            if vals:
                company.sudo().write(vals)
        if company and "website" in env.registry:
            for site in env["website"].sudo().search([]):
                vals = {"name": "DZ23 CRM"}
                if "logo" in site._fields and company.logo:
                    vals["logo"] = company.logo
                site.write(vals)
            _logger.info("DZ23 branding: site público rebrandado (DZ23 CRM).")
    except Exception as e:  # noqa: BLE001 - não pode quebrar a instalação
        _logger.warning("DZ23 branding: falha ao ativar %s: %s", lang_code, e)
