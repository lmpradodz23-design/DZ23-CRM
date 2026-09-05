# DZ23 CRM — Resumo de Arquitetura (para revisão de código)

> Contexto para análise automatizada (Codex/revisor). Descreve o que cada
> módulo faz, os modelos/fluxos e as dependências externas. Sem segredos.

## 1. O que é

**DZ23 CRM** = **Odoo 19.0 Community (LGPLv3)** rebrandado e estendido para
venda como SaaS pelo DZ23 (LEANDRO MARCOS PRADO LTDA, CNPJ 64.339.333/0001-22).
Regra de ouro: **nunca editar o core do Odoo** — tudo vive em módulos próprios
(`addons_custom/`) que herdam/estendem modelos nativos, sobrevivendo a upgrades.

- Base roda como imagem oficial `odoo:19` em Docker (não extrai o fonte do zip).
- Cores da marca: navy `#003175`, turquesa `#16B1B4`.
- Idioma padrão pt-BR; moeda BRL; fuso America/Sao_Paulo.

## 2. Runtime / execução

```
docker/docker-compose.yml   → odoo:19 + postgres:16
  odoo  :8069   monta ../addons_custom → /mnt/extra-addons
                monta ../addons_oca    → /mnt/oca-addons  (terceiros, NÃO versionado)
                config ./odoo.conf → /etc/odoo/odoo.conf
docker/evolution.yml        → Evolution API (WhatsApp não-oficial) + postgres + redis
docker/odoo.conf            → addons_path, list_db=False, dbfilter=^dz23crm$, workers=2
scripts/fetch_oca.sh        → git clone -b 19.0 dos módulos OCA
```

DB de dev: `dz23crm` (admin/admin). Backend em `/odoo`, loja em `/shop`.

> **Dependências OCA fora do zip** (baixadas por `scripts/fetch_oca.sh`):
> `helpdesk_mgmt`, `contract`, `sign_oca`, `fieldservice`. Se o revisor apontar
> import/dependência faltando desses nomes, é esperado — não estão no pacote.

## 3. Módulos próprios (`addons_custom/`)

Todos `license: 'LGPL-3'`.

| Módulo | Depende de | Função |
|---|---|---|
| `dz23_branding` | web, mail, portal | Debrand total (título/favicon/login/e-mail/portal/relatório/PWA/navbar/menu-usuário) + tema navy (SCSS) + `post_init_hook`: pt-BR padrão, OdooBot→"DZ23 Bot", empresa BRL/Brasil |
| `dz23_brasil_tools` | contacts, crm, base_geolocalize | Autofill CNPJ/CEP + enriquecimento via BrasilAPI (grátis); link wa.me; feriados/câmbio |
| `dz23_crm` | crm, mail | Ajustes de CRM p/ o nicho; link WhatsApp no lead |
| `dz23_ai` | base, mail | Serviço IA multi-provedor: `dz23.ai.chat(prompt, system, image_b64)` → dispatch Ollama/OpenAI-compat/Anthropic/Gemini; chaves nos Ajustes |
| `dz23_whatsapp` | base, mail, crm | Serviço `dz23.whatsapp`: `send_text` (Meta Cloud/Twilio/Evolution) + webhooks de entrada + provisionamento Evolution (cria instância + QR Code) |
| `dz23_agent` | dz23_whatsapp, dz23_ai, crm, calendar, sale_management, phone_validation | **Cérebro do atendente/vendedor** (ver §4) |
| `dz23_payment_woovi` | payment | Provider PIX (Woovi): cobrança via API + webhook com verificação de assinatura RSA (fail-closed) |
| `dz23_fiscal` | account | Botão "Emitir NF-e" → API de provedor terceiro (BLOQUEADO sem cert A1/token — decisão do usuário: só via terceiros) |
| `dz23_integrations` | base | Hub de 27 integradores (kanban + logos + passo-a-passo p/ pegar cada API), incl. Composio |

## 4. `dz23_agent` — fluxo do atendente (núcleo do produto)

Estende (AbstractModel `_inherit = "dz23.whatsapp"`) e sobrescreve `_on_inbound`.
Funciona igual para Meta e Evolution (o webhook normaliza número+texto).

```
Mensagem WhatsApp recebida
      │
      ▼
_agent_find_lead(número)          → acha/cria crm.lead pelo telefone; loga no chatter
      │
      ├─ intenção de AGENDA (_SCHED_RE) + data/hora (_agent_parse_datetime)?
      │     → cria calendar.event (1h)  → sincroniza p/ Google Calendar (módulo google_calendar)
      │     → responde confirmando
      │
      ├─ intenção de COMPRA (_BUY_RE) + produto do catálogo (_agent_match_product)?
      │     → abre sale.order (rascunho, sem cobrar)  → responde via IA
      │
      └─ senão → dz23.ai.chat() com CONTEXTO DINÂMICO do negócio:
              _agent_system_prompt = prompt base
                                   + _agent_business_context (empresa + catálogo product.template sale_ok)
                                   + _agent_history (últimas msgs do chatter = memória)
```

Isso torna o robô **genérico para qualquer ramo** (salão/loja/clínica/serviços):
ele descreve e vende o que estiver no catálogo daquele tenant. Se a IA estiver
indisponível, há fallback templated (nunca trava sem resposta).

Config em Ajustes: `dz23.agent.autoreply` (liga/desliga), `dz23.agent.prompt`
(personalidade). Todos via `ir.config_parameter` — nada hardcoded.

## 5. Integração de calendário (agendamento em tempo real)

- `calendar` (nativo): o robô cria `calendar.event`.
- `google_calendar` (nativo, **instalado**): sync bidirecional. Cron
  "Google Agenda: sincronização". OAuth em Ajustes (`cal_client_id`/
  `cal_client_secret`) — **preenchido pelo usuário**, não no código.

## 6. Política de segredos (arquitetural, inegociável)

- Código referencia **apenas nomes** de parâmetros (`dz23.ai.*`, `dz23.whatsapp.*`,
  etc.) lidos de `ir.config_parameter`.
- Valores reais → só nos Ajustes do Odoo (DB) ou `.env` do servidor. Nunca em
  git/código/log. `.env.example` versiona apenas os nomes.
- Webhooks verificam assinatura: Woovi RSA-SHA256 (fail-closed), Meta
  HMAC-SHA256 `X-Hub-Signature-256`.

## 7. Estado verificado (2026-09-05)

- 142 módulos carregam limpos; os 9 DZ23 instalam sem erro.
- WhatsApp testado **AO VIVO** via Evolution: cliente agendou por mensagem real
  e o robô respondeu + criou o evento (`calendar.event` 2026-09-10 14:30).
- Venda testada E2E: "quanto custa X?" → abriu orçamento `sale.order`.
- IA (Ollama llama3.2:1b) responde ao vivo usando o catálogo.

## 8. Bloqueios externos honestos (não são bugs de código)

- WhatsApp produção business-initiated: templates + verificação Meta (dias–semanas).
- NF-e ao vivo: certificado e-CNPJ A1 + token do provedor + contador.
- Woovi/Stripe/Mercado Pago ao vivo: credenciais de produção nos Ajustes.
- Google Calendar sync real: OAuth Client ID/Secret do Google Cloud nos Ajustes.
- Áudio↔áudio (STT/TTS) e console de atendimento single-screen (OWL): não implementados.

## 9. Pontos que valem revisão do Codex

- Robustez de parsing de data/hora em `dz23_agent` (formatos pt-BR variados).
- `_agent_match_product`: casamento por substring — pode ser frágil com nomes curtos.
- Tratamento de rate limit/cache nas chamadas BrasilAPI (`dz23_brasil_tools`).
- Idempotência dos webhooks (Woovi/Meta/Evolution) contra reentrega.
- Cobertura de testes automatizados (hoje a verificação é via shell E2E manual).
