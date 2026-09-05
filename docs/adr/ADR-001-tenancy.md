# ADR-001 — Modelo de Tenancy do DZ23 CRM (SaaS)

- Status: **Aceito** (direção padrão) — 2026-09-05
- Contexto do produto: DZ23 CRM vendido como SaaS multi-cliente sobre Odoo 19
  Community. Hoje o fluxo público (webhooks WhatsApp, agente IA, catálogo)
  usa `sudo()`, parâmetros globais (`ir.config_parameter`) e `env.company`
  implícita; o lead é buscado pelos últimos 8 dígitos do telefone e o catálogo
  não tem escopo explícito de empresa. Isso é inseguro para multi-tenant.

## Decisão

**Banco por tenant (database-per-tenant) é a direção PADRÃO para novos
clientes.** Cada cliente do SaaS recebe um banco Odoo isolado. Isolamento
forte por construção: nenhum vazamento cruzado de dados possível via ORM,
backups/restore por cliente, upgrade e limites de recurso por cliente.

Como o Odoo já gerencia múltiplos bancos no mesmo servidor, o provisionamento
é: criar banco a partir de um template com os módulos DZ23 instalados +
`dbfilter` por host/subdomínio (ex.: `^cliente1$`), atrás do reverse proxy.

### Alternativa permitida (banco compartilhado / multi-company)

Só é aceitável **com** um modelo de canal explicitamente company-scoped e
testes adversariais cross-tenant passando (ver P0-C). Requisitos mínimos:

- toda tabela de negócio com `company_id` + `check_company=True` nas relações;
- `record rules` por empresa em todos os modelos expostos;
- credenciais/prompt por canal/empresa, nunca em parâmetro global;
- resolução de canal por identificador opaco (não por company implícita);
- proibição de busca global por cauda de telefone.

O banco compartilhado tem maior superfície de risco (um bug de record rule
vaza tudo) e é adotado só quando a densidade de clientes pequenos justificar
o custo de RAM do banco-por-tenant.

## Consequências

- **Novos clientes:** provisionar banco isolado (script de template + dbfilter).
- **Banco atual `dz23crm` (compartilhado, já em uso):** não migramos à força;
  aplicamos os contratos de channel/company do P0-C para que, enquanto for
  compartilhado, o isolamento seja garantido por company_id + record rules +
  canais com credencial própria. Isso também deixa o código pronto para operar
  idêntico nos dois modelos.
- **Segredos:** saem de `ir.config_parameter` global para o registro de canal
  (por empresa), lidos com escopo — alinhado à política de segredos do projeto.

## Implementação (rastreamento — P0-C)

1. Modelo `dz23.channel` (um canal ↔ exatamente uma `company_id`), com
   provider (meta/evolution), credenciais próprias e prompt próprio.
2. Webhook resolve o canal por identificador opaco + instância validada e
   opera com `with_company(channel.company_id)` / `allowed_company_ids`.
3. Telefone canônico E.164 + provider user/channel id, com unicidade por canal.
4. `check_company`, `company_id` e `record rules` em lead/evento/pedido/canal.
5. Proibir busca global por 8 dígitos (escopar por canal/empresa).
6. Dois tenants de teste + provas adversariais de leitura/escrita/ação cruzada
   com usuário comum e via webhook (devem falhar).
