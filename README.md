<div align="center">

# DZ23 CRM

**Sistema de Gestão de Relacionamento** — CRM open source em português,
construído sobre o [Odoo 19 Community](https://github.com/odoo/odoo).

[![Licença: LGPL v3](https://img.shields.io/badge/Licença-LGPL%20v3-blue.svg)](LICENSE)
[![Base: Odoo 19](https://img.shields.io/badge/Base-Odoo%2019%20Community-875A7B.svg)](https://github.com/odoo/odoo)
[![PT-BR](https://img.shields.io/badge/Idioma-Português%20(BR)-009c3b.svg)](#)

</div>

---

## O que é

O **DZ23 CRM** é uma plataforma de CRM pronta para o Brasil: gestão de leads,
clientes, funil de vendas e agenda — em **português**, instalável como **app
(PWA)** no celular e no desktop, com **notificações push** nativas.

É software livre: você pode usar, estudar, modificar e hospedar. Ele estende o
Odoo por **módulos próprios** (nunca editando o núcleo), então continua
atualizável.

## Recursos

- 🎨 **Marca própria** — interface, login, e-mails, relatórios e app 100% DZ23.
- 🇧🇷 **Português do Brasil** como idioma padrão.
- 📱 **App PWA** instalável + **push** no navegador (nativo do Odoo 19).
- 🏢 **Autopreenchimento por CNPJ/CEP** e enriquecimento de lead (via BrasilAPI, grátis).
- 💬 **WhatsApp** plugável — Meta Cloud API, Twilio ou Evolution.
- 💳 **Pagamentos** — Stripe e Mercado Pago (nativos) + Woovi/PIX *(em construção)*.
- 🧾 **NF-e** via provedor (Focus NFe / NFe.io / Nuvem Fiscal) *(em construção)*.

## Módulos (`addons_custom/`)

| Módulo | Função |
|---|---|
| `dz23_branding` | Rebrand completo + pt-BR padrão + PWA/push |
| `dz23_brasil_tools` | Autofill CNPJ/CEP, enriquecimento, WhatsApp (wa.me), feriados, câmbio |
| `dz23_crm` | Ajustes de CRM (link rápido de WhatsApp no lead) |
| `dz23_whatsapp` | Envio de WhatsApp plugável (Meta / Twilio / Evolution) |

## Instalação rápida (Docker)

```bash
git clone <url-do-seu-repositorio> dz23-crm
cd dz23-crm/docker
cp ../.env.example ../.env      # edite as senhas de desenvolvimento
docker compose up -d
docker compose run --rm odoo odoo -d dz23crm \
  -i base,dz23_branding,dz23_brasil_tools,dz23_crm,dz23_whatsapp \
  --load-language=pt_BR --stop-after-init
docker compose up -d
```
Acesse **http://localhost:8069** (base `dz23crm`). Detalhes e verificação em
[`docs/README.md`](docs/README.md).

## Licença

Distribuído sob **LGPL-3.0** (ver [LICENSE](LICENSE)). Como obra derivada do
Odoo (LGPLv3), os módulos mantêm a mesma licença e os avisos de copyright do
Odoo são preservados. "DZ23" e "DZ23 CRM" são marcas do titular; "Odoo" é marca
da Odoo S.A. e não é usada para promover este projeto.

## Contribuindo

Toda ajuda é bem-vinda — código, tradução, design ou documentação.
Veja [CONTRIBUTING.md](CONTRIBUTING.md).

## Segurança

Nunca cometa segredos. Credenciais ficam só no `.env` (fora do Git) ou no
Credential Vault do Odoo. Encontrou uma vulnerabilidade? Escreva para
**contato@dz23.com.br** em vez de abrir uma issue pública.
