# Contribuindo com o DZ23 CRM

Que bom que você quer ajudar! 💙 Aqui vai o essencial para contribuir com
carinho e sem dor de cabeça.

## Formas de contribuir
- **Código** — corrigir bugs, criar módulos, melhorar os existentes.
- **Tradução** — revisar/ampliar o português (ou outros idiomas).
- **Design** — telas, ícones, identidade visual.
- **Documentação** — tutoriais, exemplos, este guia.

## Como propor uma mudança
1. Faça um **fork** do repositório.
2. Crie um branch: `git checkout -b minha-melhoria`.
3. Faça as alterações **em módulos** (`addons_custom/`) — **nunca** edite o
   núcleo do Odoo.
4. Rode a verificação local (ver [`docs/README.md`](docs/README.md)).
5. Faça commit e abra um **Pull Request** descrevendo o quê e o porquê.

## Regras de ouro
- **Licença:** todo módulo nasce com `"license": "LGPL-3"` no `__manifest__.py`
  (o projeto é LGPL-3, derivado do Odoo). Ao contribuir, você concorda em
  licenciar sua contribuição sob LGPL-3.
- **Sem segredos:** nunca faça commit de `.env`, tokens, chaves ou certificados.
  Use `.env` (fora do Git) e nomes de variáveis no código.
- **Toda feature nasce com verificação** — descreva no PR como testou.
- **Migrations nunca destrutivas.**
- **pt-BR** nas strings voltadas ao usuário.
- Mantenha arquivos enxutos e legíveis, no padrão do código ao redor.

## Padrão de módulo
```
addons_custom/<seu_modulo>/
├── __manifest__.py     # depends, license LGPL-3
├── __init__.py
├── models/  views/  data/  controllers/  static/
```

## Código de conduta
Seja gentil e respeitoso. Discutimos ideias, não pessoas. Contribuições e
issues devem manter um ambiente acolhedor para todo mundo.

## Dúvidas
Abra uma *issue* com a etiqueta `pergunta` ou fale com a equipe DZ23.
Obrigado por construir junto! 🚀
