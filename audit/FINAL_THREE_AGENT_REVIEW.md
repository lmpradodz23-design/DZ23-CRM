# Auditoria Final — DZ23 CRM

Auditoria independente (Architect + Security + QA) sobre os 6 módulos em
`addons_custom/`, seguida de correção pela causa raiz e reverificação.

## Achados e desfechos

| # | Sev | Achado | Desfecho |
|---|-----|--------|----------|
| 1 | CRITICAL | Webhook Woovi confirmava pagamento sem verificar assinatura (fraude) | **FIXED+verificado**: assinatura RSA-SHA256 obrigatória (fail-closed) + checagem de valor. POST sem assinatura → HTTP 401 (testado). |
| 2 | HIGH | Webhook WhatsApp sem validar origem (HMAC Meta) | **FIXED+verificado**: HMAC X-Hub-Signature-256 obrigatório; POST inválido → 401 (testado). |
| 3 | MEDIUM | PII/dados de pagamento em log | **FIXED**: webhooks logam só metadados. |
| 4 | MEDIUM | HTTP externo em `@api.onchange` (CNPJ/CEP) pode travar worker | **ACEITO (tradeoff)**: autofill foi requisito do usuário; dispara só no comprimento exato (8/14), timeout curto, e há botões manuais. Reavaliar como job assíncrono se houver carga alta. |
| 5 | MEDIUM | `final_message` do brand promotion vira `%s%s` | **OK**: o template interpola via `t-out=... % (...)`; resultado renderiza "DZ23 CRM". Sem "Powered by". |
| 6 | MEDIUM | Rota/headers do provedor de NF-e são genéricos | **BLOCKED (externo)**: emissão requer certificado A1 + conta do provedor; adaptador por provedor é trabalho de go-live. Documentado. |
| 7 | LOW | `send_text` do WhatsApp sem gatilho | **INFO**: é biblioteca para uso programático/automação; envio via config validado. |
| 8 | LOW | Arredondamento de centavos em float | **FIXED**: `float_round`. |
| 9 | LOW | `branding_data` `noupdate=0` reaplica no upgrade | **INTENCIONAL**: garante o debrand; em multi-tenant, tenant ajusta. |
| 10 | LOW | XPaths de debrand por `contains('odoo.com')` | **ACEITO**: instala e funciona no 19.0; revisar em upgrades de minor. |

## Pontos positivos confirmados pela auditoria
- Nenhum segredo hardcoded (tudo em `ir.config_parameter`/campo do provider, com `password=True` e `groups=base.group_system` no AppID Woovi).
- Timeouts + tratamento de erro em todas as chamadas externas.
- Sanitização de entrada (`only_digits`, regex) mitiga SSRF/injeção; base URLs vêm de config admin.
- Sem `eval/exec/os.system`; sem `.env`/segredos rastreados no Git.

## Gates
- init/build (instala os 6): **PASS** ("Modules loaded.")
- funcional (CNPJ/CEP ao vivo, provider, empresa/logo, pt-BR, login pt-BR): **PASS**
- segurança (webhooks fail-closed 401/403 testados; scan de segredos): **PASS**
- CRITICAL=0, HIGH=0 (corrigidos e reverificados): **PASS**

## Blockers externos (honestos — não são falhas internas)
- **Woovi PIX ao vivo**: AppID/sandbox + chave pública do webhook + URL pública.
- **NF-e emissão**: certificado e-CNPJ A1 + conta de provedor + validação contábil + adaptador por provedor.
- **WhatsApp produção (mensagens iniciadas)**: templates aprovados pela Meta.
