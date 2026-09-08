# DZ23 CRM — Scorecard de Qualidade

Critérios objetivos e verificáveis (2026-09-08, branch `main`).

| Dimensão | Critério | Status | Evidência |
|---|---|---|---|
| Segurança | 0 CRITICAL / 0 HIGH em 2 rodadas de auditoria (3 agentes cada) | ✅ | `audit/FINAL_THREE_AGENT_REVIEW_2026-09-07.md`, `audit/REAUDIT_2026-09-08.md` |
| Segredos | 0 vazamentos no histórico | ✅ | `gitleaks detect` (44 commits) |
| Segredos | `.env` fora do Git; credenciais de canal só-admin | ✅ | `.gitignore`, `groups="base.group_system"` |
| Webhooks | Fail-closed + auth (HMAC/RSA/segredo) + limite de corpo | ✅ | `dz23_whatsapp/controllers/main.py`, `dz23_payment_woovi/controllers/main.py` |
| Confiabilidade | Inbox + Outbox duráveis (idempotência, retry/backoff, DLQ) | ✅ | `message_inbox.py`, `message_outbox.py` + tela DLQ |
| Multi-tenant | Isolamento por empresa (canais, inbox, outbox, agenda) | ✅ | record rules + `opportunity_id.company_id` |
| Testes | Suíte `dz23` 40/40 (0 falhas/0 erros) | ✅ | `odoo --test-tags dz23` |
| Instalação | Instalação LIMPA de todos os módulos num DB novo | ✅ | "Modules loaded." em `dz23_ci` |
| Lint/format | `ruff check` + `ruff format` limpos | ✅ | `ruff` |
| Supply chain | Imagens por digest; OCA por commit; CI actions por SHA | ✅ | `docker/*.yml`, `dependencies.lock.yml`, `.github/workflows/ci.yml` |
| CI | ruff + gitleaks + bandit + semgrep + trivy + SBOM | ✅ | `.github/workflows/ci.yml` |
| Licença | MIT (código DZ23); manifests com enum válido do Odoo | ✅ | `LICENSE`, `NOTICE.md` |
| Saúde OSS | README, SECURITY, CHANGELOG, CONTRIBUTING, templates, CODEOWNERS, dependabot | ✅ | raiz + `.github/` |
| Runtime | Servidor vivo responde HTTP 200 com o código atual | ✅ | `curl /web/login` |
| Entrega | Envio WhatsApp exatamente-uma-vez (guarda + commit por registro) | ✅ | `message_outbox.py`, `test_cron_sends_once_no_duplicate` |
| Smoke E2E | Instalação do zero + suíte (41/41) em DB descartável | ✅ | `scripts/smoke.sh` |
| Release | Tag `v*` gera SBOM + GitHub Release | ✅ | `.github/workflows/release.yml` |

## Limitações conhecidas (documentadas honestamente)
- Entrega de resposta WhatsApp *at-least-once* (provedores sem idempotency key nativa; `provider_message_id` registrado).
- Redação de PII cobre e-mail/telefone/CPF/CNPJ (não nome/endereço livres).
- NF-e e Woovi/PIX ao vivo dependem de certificado A1 / conta do provedor.
- `proxy_mode=True`: produção deve ter reverse proxy limpando `X-Forwarded-*` (ver SECURITY.md).

Nenhuma dessas é um defeito aberto — são dependências externas ou trade-offs registrados.
