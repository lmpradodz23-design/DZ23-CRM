# Matriz de Paridade — Enterprise → Open Source (DZ23 CRM)

> Objetivo: substituir recursos pagos do Odoo Enterprise por alternativas
> livres (Community + OCA + código DZ23), sem copiar código Enterprise e sem
> paywall bypass. Um conector OSS não torna o serviço externo (WhatsApp,
> Google, bancos, PSPs, provedores fiscais) gratuito nem open source.
>
> Colunas **Instalado** e **Testes** ficam **PENDENTE DE VERIFICAÇÃO** até
> serem confirmadas contra o banco (`ir.module.module` + `to_buy=true`) e a
> execução dos testes — não declarar paridade sem evidência.
>
> Licenças: Community/OCA sob **LGPL-3** ou **AGPL-3** (verificar por módulo
> antes de embarcar; AGPL tem implicações em SaaS — registrar no THIRD_PARTY).

| Recurso Enterprise | Alternativa OSS | Upstream | Licença | Maturidade 19.0 | Instalado | Testes |
|---|---|---|---|---|---|---|
| Accounting (Accountant) | `account` + OCA account-financial-tools/reporting + l10n-brazil | OCA/account-* | (A)GPL-3 | Média (l10n-brazil 19 em transição — ver ADR-002) | PENDENTE | PENDENTE |
| Appointment | `resource_booking` | OCA/calendar | AGPL-3 | Média | PENDENTE | PENDENTE |
| Helpdesk | `helpdesk_mgmt` (+crm/project/sale/rating conforme necessidade) | OCA/helpdesk | AGPL-3 | Boa | SIM (fetch_oca) | PENDENTE |
| Field Service | `fieldservice` (+calendar/stock/sign/timesheet) | OCA/field-service | AGPL-3 | Boa | SIM (fetch_oca) | PENDENTE |
| Sign | `sign_oca` | OCA/sign | AGPL-3 | Boa | SIM (fetch_oca) | PENDENTE |
| Subscription | `contract` (+contract_sale/subscription_oca conforme fluxo) | OCA/contract | AGPL-3 | Boa | SIM (fetch_oca) | PENDENTE |
| Knowledge | `document_page`, `document_knowledge` | OCA/knowledge | AGPL-3 | Média | PENDENTE | PENDENTE |
| Documents (DMS) | `dms` | OCA/dms | AGPL-3 | Média | PENDENTE | PENDENTE |
| Marketing Automation | `mass_mailing` + Mautic self-hosted OU módulo DZ23 | core + externo | LGPL-3 | Parcial | Parcial (mass_mailing) | PENDENTE |
| Quality/MRP/PLM | OCA/manufacture (só módulos 19 estáveis) | OCA/manufacture | AGPL-3 | Variável | PENDENTE | PENDENTE |
| Barcode | OCA/stock-logistics-barcode | OCA | AGPL-3 | Só após migração 19 aprovada | PENDENTE | PENDENTE |
| Planning/Timesheet | core + OCA timeline/resource_booking | core + OCA | (A)GPL-3 | Média | PENDENTE | PENDENTE |
| VoIP | Asterisk/FreeSWITCH + SIP.js + bridge DZ23 | externo + DZ23 | — (externo) | A construir | NÃO | PENDENTE |
| Mobile | PWA responsiva + Web Push (core) | core `web`/`mail` | LGPL-3 | Boa | SIM (dz23_branding) | PENDENTE |
| Studio | Customizações viram módulos versionados; `base_custom_info` p/ campos simples | OCA/DZ23 | (A)GPL-3 | — | Parcial | PENDENTE |
| Amazon / Social / WhatsApp / bancos | Conector OSS DZ23; **API externa continua proprietária/paga** | DZ23 | LGPL-3 (conector) | Parcial | Parcial | PENDENTE |

## Módulos pagos/IAP a desativar (após mapear dependências + backup)

Confirmar presença/uso no banco antes de remover. Provar depois que **não há
mais chamadas automáticas por crédito**:

- `crm_iap_enrich`, `crm_iap_mine` e IAP associado (enriquecimento pago).
- `sms` (IAP de SMS) — se não usado.
- `snailmail*` (correspondência física paga).
- Conectores externos não usados.

## Princípio de instalação

Instalar **por jornada real** (atender, vender, entregar, receber), não tudo
indiscriminadamente. Manter a UI simples. Cada módulo OCA embarcado deve ser
**pinado por SHA** em `dependencies.lock.yml` e passar em teste antes de entrar.

## A fazer para fechar esta matriz (com evidência)

1. Ler `ir.module.module` no banco: quais têm `to_buy=true` (Enterprise) e
   quais dos OCA acima estão de fato `installed`.
2. Preencher **Instalado** com o estado real e **Testes** com o resultado da
   suíte por jornada.
3. Registrar licença exata + commit/SHA de cada OCA em `THIRD_PARTY_NOTICES`.
