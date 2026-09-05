# DZ23 CRM (sobre Odoo 19 Community)

Rebrand/plataforma DZ23 CRM. Base: **Odoo 19 Community (LGPLv3)** — obra
derivada; a licença e os avisos de copyright da base são mantidos.

## Estrutura
```
DZ23-CRM/
├─ addons_custom/dz23_branding/   # Fase 1 — rebrand/debrand (DZ23 CRM)
├─ brand/                         # logo original + assets gerados
├─ docker/                        # ambiente de dev/teste (Odoo 19 + Postgres)
└─ docs/                          # este README + referência de templates Odoo
```

## Subir o ambiente de teste (dev)
Pré-requisitos: Docker Desktop rodando.
```bash
cd docker
cp ../.env.example ../.env   # e edite as senhas de DEV
docker compose up -d
# Primeira vez: criar a base e instalar o módulo de branding
docker compose run --rm odoo odoo -d dz23crm -i base,dz23_branding --stop-after-init
docker compose up -d
```
Acesse http://localhost:8069  (base: `dz23crm`).

Reinstalar o branding após mudanças:
```bash
docker compose run --rm odoo odoo -d dz23crm -u dz23_branding --stop-after-init
docker compose restart odoo
```

## Verificação da Fase 1 (debrand) — checklist
- [ ] Aba do navegador mostra **DZ23 CRM** (não "Odoo").
- [ ] Favicon é o emblema DZ23.
- [ ] Tela de **login**: logo DZ23; rodapé **sem** "Powered by Odoo".
- [ ] Menu do usuário: **sem** "My Odoo.com Account"; "Ajuda" aponta p/ DZ23.
- [ ] E-mail de notificação: rodapé **sem** "Powered by Odoo".
- [ ] Portal do cliente: sidebar **sem** "Powered by Odoo".
- [ ] Relatório PDF: rodapé com dados do DZ23.
- [ ] `LICENSE`/`COPYRIGHT` do Odoo intactos (não removidos).

## Docker travando ("An unexpected error occurred")
Se o Docker Desktop fechar com erro `starting services: initializing Inference
manager ... dockerInference: The file cannot be accessed`, é um bug do recurso
**Model Runner / Docker AI (Inference)**, não do projeto. Correções:
1. Settings → **Features in development** → desmarcar **Docker AI / Model Runner (Inference)**; Apply & Restart.
2. Se persistir: fechar Docker, apagar `C:\Users\zodyp\AppData\Local\Docker\run\` e reabrir.
3. Último recurso: **Reset to factory defaults** no próprio diálogo de erro.
Alternativa sem Docker: instalador oficial Odoo 19 para Windows (.exe) — ver Fase 8.

## Notas
- **Segredos**: só no `.env` (fora do Git) / Vault do Odoo; em dev, chaves de
  TESTE. Nunca commitar valores.
- **Não** editar o core do Odoo — tudo via módulos em `addons_custom/`.
- Deploy em servidor do DZ23: só com confirmação explícita.
