# AUTONOMOUS MISSION STATE — DZ23 CRM correção pós-reauditoria

- mission_id: dz23-post-reaudit-2026-09-05
- objetivo: fechar HIGH/MEDIUM da reauditoria (DZ23_CRM_REAUDITORIA_P0_ED39FAB) em 6 ondas, cada uma testada e commitada.
- branch: hardening/post-audit (a partir de df75128)
- estado: EXECUTING
- critérios de aceite: gates locais verdes (testes dz23), isolamento cross-tenant provado sem sudo mascarar, idempotência (1 efeito por message_id), agente determinístico, privacidade IA, roles PG sem BYPASSRLS, /tmp/odoo.conf 0600, CI reprodutível; externos = BLOCKED_EXTERNAL.

## Ondas
- Onda 0 — segredos: **DONE** (commit 15aa28d). Rotação Evolution (old->401/new->200), callback_secret por canal (admin key->401), gitleaks allowlist removida, Evolution sem porta no host. Testes 12/12.
- Onda 1 — P0-C gaps: provider_channel_id + unique(provider,provider_channel_id); identidade provider_user_id (dz23.channel.contact) unique(channel,provider_user_id); sair de sudo() p/ usuário técnico sujeito a record rules. **IN PROGRESS**
- Onda 2 — inbox/outbox idempotente + worker + DLQ. PENDENTE
- Onda 3 — agente determinístico + persona honesta "assistente virtual". PENDENTE
- Onda 4 — privacidade IA + Gemini header + logger redaction. PENDENTE
- Onda 5 — roles PG + /tmp/odoo.conf 0600 + Ollama rede privada + digests + upgrade fiscal. PENDENTE (ops delicadas -> checkpoint)
- Onda 6 — IAP pago + Ruff (102) + CI locks/SBOM. PENDENTE

## Runtime atual
- dz23net conecta odoo/evolution/ollama por nome; odoo 127.0.0.1:8069; evo interno; ollama 0.0.0.0:11434 (Onda 5).
- Canal id=1 token=4jhPSUn4O-uKOdUbSitkV6716klzsTmH, evo_instance=dz23crm, callback_secret set, WhatsApp state=open.
- Evolution admin key rotacionada (só no docker/.env). webhook_base=http://docker-odoo-1:8069. IA: dz23-ollama:11434, llama3.2:3b.

## próxima ação
Onda 1: provider_channel_id+constraint, modelo identidade, usuário técnico, sair do sudo; seed 2ª empresa; testes adversariais 2 empresas mesmo sufixo.
