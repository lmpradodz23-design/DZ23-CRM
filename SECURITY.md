# Política de Segurança

## Como reportar uma vulnerabilidade

**Não** abra uma issue pública para vulnerabilidades. Envie um e-mail para
**contato@dz23.com.br** com:

- descrição do problema e impacto;
- passos para reproduzir (PoC, se houver);
- versão/commit afetado.

Você receberá uma confirmação em até **72 horas** e um plano de correção. Pedimos
um prazo razoável de divulgação coordenada antes de tornar o detalhe público.

## Escopo

Este repositório contém apenas os módulos originais DZ23 (`addons_custom/`,
`docker/`, `scripts/`). Vulnerabilidades no **Odoo** (LGPL, não redistribuído
aqui) devem ir para a Odoo S.A.; nos módulos **OCA**, para a OCA.

## Boas práticas já aplicadas

- Segredos **nunca** no Git (só em `.env` fora do versionamento ou no vault do Odoo);
  varredura `gitleaks` no CI.
- Webhooks **fail-closed** com autenticação (HMAC Meta / RSA Woovi / segredo de
  callback Evolution) e limite de corpo.
- Credenciais de canal legíveis só por administrador.
- Imagens Docker e dependências OCA **pinadas** (digest / commit); actions do CI
  pinadas por SHA.
- Gate de privacidade para IA externa (consentimento LGPD + redação de PII).

## Produção

O Odoo deve ficar **atrás de um reverse proxy** que sobrescreva/limpe cabeçalhos
`X-Forwarded-*` do cliente (o `proxy_mode` confia neles). Nunca exponha o Odoo
diretamente à internet.
