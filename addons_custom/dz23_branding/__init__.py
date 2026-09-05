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
    except Exception as e:  # noqa: BLE001 - não pode quebrar a instalação
        _logger.warning("DZ23 branding: falha ao ativar %s: %s", lang_code, e)
