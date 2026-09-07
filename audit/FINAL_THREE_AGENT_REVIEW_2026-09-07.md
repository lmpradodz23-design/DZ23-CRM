# DZ23 CRM — Auditoria Final por 3 Agentes Independentes (2026-09-07)

Branch: `hardening/post-audit` · Odoo 19 Community
Instância viva auditada: http://127.0.0.1:8069 (db `dz23crm`).
(Rodada posterior à FINAL_THREE_AGENT_REVIEW.md — foca nas Ondas 0–6.)

Três auditores independentes (Arquitetura, Segurança ofensiva, Produto/QA)
revisaram código + instância viva SEM ver as conclusões uns dos outros.
Consolidação e correção pela causa raiz. Gate: CRITICAL=0 e HIGH=0.

## Veredito por auditor
- **A — Arquitetura:** 0 CRITICAL, 1 HIGH, vários MEDIUM/LOW.
- **B — Segurança (ofensiva):** 0 CRITICAL, 0 HIGH, MEDIUM/LOW (defesa em profundidade).
- **C — Produto/QA:** 0 CRITICAL, 2 HIGH, MEDIUM/LOW.

## HIGH (gate) — corrigidos e reverificados (33/33 testes)

| # | Origem | Achado | Correção |
|---|--------|--------|----------|
| H1 | A | Resposta ao cliente "fire-and-forget": falha de envio engolida, sem retry/DLQ | **Outbox durável** `dz23.message.outbox` (retry+backoff+jitter+DLQ) + cron; `handle_inbound` enfileira a resposta (efeito aplicado 1x, envio reenviável) |
| H2 | C | Botão "Conectar WhatsApp (QR)" retornava dict cru → QR nunca aparecia; Ajustes conectava canal padrão, não o aberto | `action_evolution_connect` abre o wizard vinculado ao canal atual; lógica em `_evolution_provision`; wizard usa `channel_id` |
| H3 | C | Provedores de IA externos inutilizáveis: gate `dz23.ai.external_allowed` sem toggle em tela | Booleano de consentimento (LGPD) em Ajustes › DZ23 IA |

## MEDIUM — corrigidos
- **MED-1 (B):** segredos do canal com `groups="base.group_system"`; envio/webhook leem via `sudo()`. Não mais legíveis por `group_user`.
- **MED-01 (A):** inbox/outbox usam `clock_timestamp() AT TIME ZONE 'utc'` (fuso).
- **MED-2 (B):** `evolution.yml` (postgres/redis/evolution-api) e `ollama.yml` pinados por `@sha256`.
- **MED-3 (C):** Ajustes do agente = PADRÃO de novos canais (defaults ligados aos parâmetros); help explícito.
- **item 6 (C):** views + menus (admin) de Inbox/Outbox com Reprocessar/Reenviar (DLQ visível).
- **item 4 (C):** promo "Powered by Odoo/Crie um site grátis" escondido (CSS no `<head>`).
- **item 5 (C):** `web.base.url` `http://odoo:8069` → `http://localhost:8069`.

## LOW / IMPROVEMENT — corrigidos
- **LOW-1 (B):** `dz23_integration.how_to` → `sanitize=True`.
- **LOW-02/IMP-1 (A/B):** envio de IMAGEM a IA externa bloqueado (privacidade).
- **item 9 (C):** copy "Registrei seu pedido" → "Preparei seu orçamento".

## Limitações conhecidas / dependências externas (honestas)
- **MED-04/LOW-3 calendário multi-tenant:** `calendar.event` (Odoo 19 CE) NÃO tem `company_id`; anti-double-booking é global. OK hoje (single-tenant); isolar exigirá calendário-recurso por empresa. (Tentativa de filtro por company_id revertida por inexistência do campo.)
- **MED-02/03 idempotência de efeito / chamadas longas:** envio saiu da transação do inbox (outbox). Criação de orçamento/evento e chamada de IA ainda na transação do worker; risco residual só em rollback pós-efeito (mitigado por savepoint). Futuro: idempotência por message_id.
- **NF-e / Woovi:** fail-closed; dependem de certificado/homologação/conta externas.
- **PG role split (HIGH-03 reauditoria):** script pronto; ownership exige backup + janela (não auto-aplicado).
- **LOW-2 (B):** chave DEV fraca antiga no histórico (não live; gitleaks 0 vazamentos).

## Gate final
- CRITICAL = 0 · HIGH = 0 (3/3 corrigidos e reverificados)
- Testes (tag dz23): 33/33 PASS (dz23_agent 12, dz23_ai 7, dz23_whatsapp 24)
- ruff = PASS · compileall = PASS · gitleaks = 0 vazamentos (40 commits)
