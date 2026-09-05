#!/usr/bin/env bash
# Baixa os módulos OCA (open source, grátis) usados pelo DZ23 CRM, na versão 19.0.
# OCA = Odoo Community Association (github.com/OCA). Módulos AGPL/LGPL, legais.
# Uso: bash scripts/fetch_oca.sh   (a partir da raiz do projeto)
set -e
BRANCH="19.0"
DEST="addons_oca"
mkdir -p "$DEST"

# repo -> equivalente open source do recurso Enterprise
REPOS=(
  "helpdesk"       # Central de Ajuda (Helpdesk)
  "contract"       # Assinaturas / faturamento recorrente
  "sign"           # Assinatura digital de documentos
  "field-service"  # Ordens de serviço em campo (Field Service)
)

for repo in "${REPOS[@]}"; do
  if [ -d "$DEST/$repo/.git" ]; then
    echo "== atualizando $repo =="
    git -C "$DEST/$repo" pull --ff-only || true
  else
    echo "== clonando OCA/$repo ($BRANCH) =="
    git clone --depth 1 -b "$BRANCH" "https://github.com/OCA/$repo.git" "$DEST/$repo"
  fi
done

echo "OK. Ajuste o addons_path do Odoo para incluir cada repo em $DEST/ (ver docker/odoo.conf)."
