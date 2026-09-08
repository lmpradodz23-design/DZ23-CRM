# -*- coding: utf-8 -*-
# Semeia um dz23.channel para a empresa atual a partir dos parâmetros globais
# antigos (ir.config_parameter), para o fluxo já configurado continuar funcionando
# no novo modelo multi-tenant. Não faz chamada de rede (repontar o webhook para a
# URL tokenizada é feito fora da migração).
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    Channel = env["dz23.channel"]
    ICP = env["ir.config_parameter"].sudo()
    company = env.company

    if Channel.search([("company_id", "=", company.id)], limit=1):
        _logger.info("dz23_whatsapp: canal já existe p/ %s, migração ignora.", company.name)
        return

    provider = (ICP.get_param("dz23.whatsapp_provider", "evolution") or "evolution").strip()
    vals = {
        "name": "WhatsApp %s" % company.name,
        "company_id": company.id,
        "provider": provider if provider in ("evolution", "meta_cloud", "twilio") else "evolution",
        "evo_base": ICP.get_param("dz23.whatsapp.evolution_base") or False,
        "evo_instance": ICP.get_param("dz23.whatsapp.evolution_instance") or False,
        "evo_apikey": ICP.get_param("dz23.whatsapp.evolution_apikey") or False,
        "meta_phone_id": ICP.get_param("dz23.whatsapp.meta_phone_id") or False,
        "meta_token": ICP.get_param("dz23.whatsapp.meta_token") or False,
        "meta_app_secret": ICP.get_param("dz23.whatsapp.meta_app_secret") or False,
        "meta_verify_token": ICP.get_param("dz23.whatsapp.webhook_verify_token") or False,
        "agent_autoreply": (ICP.get_param("dz23.agent.autoreply", "1") or "1") not in ("0", "False", "false"),
        "agent_prompt": ICP.get_param("dz23.agent.prompt") or False,
    }
    channel = Channel.create(vals)
    # Não logar o webhook_token (token opaco de roteamento) — CLAUDE.md §6.
    _logger.info("dz23_whatsapp: canal '%s' criado (id=%s) na migração.",
                 channel.name, channel.id)
