<!-- Obrigado por contribuir! Descreva a mudança e marque os itens. -->

## O que muda

<!-- Resumo objetivo. Ligue a issue: "Closes #123" -->

## Como testar

```bash
docker exec docker-odoo-1 bash -c 'odoo -c /tmp/odoo.conf -d dz23crm \
  -u <modulo> --test-enable --test-tags dz23 --stop-after-init --workers=0 --http-port=8098'
```

## Checklist

- [ ] `ruff check addons_custom` e `ruff format` limpos
- [ ] Testes da tag `dz23` passam (0 falhas)
- [ ] Nenhum segredo commitado (`.env` fora do Git)
- [ ] Migração (se houver) é não destrutiva
- [ ] Feature nova acompanha teste
- [ ] Não edita o núcleo do Odoo (só `addons_custom/`)
