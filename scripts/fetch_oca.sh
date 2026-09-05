#!/usr/bin/env bash
# Baixa os módulos OCA (open source, grátis) usados pelo DZ23 CRM, na versão 19.0,
# TRAVADOS no commit exato de dependencies.lock.yml (reprodutível; não segue a
# branch mutável 19.0). OCA = Odoo Community Association. Módulos AGPL/LGPL.
# Uso: bash scripts/fetch_oca.sh   (a partir da raiz do projeto)
set -euo pipefail
DEST="addons_oca"
mkdir -p "$DEST"

# repo -> commit pinado (manter em sincronia com dependencies.lock.yml)
declare -A PIN=(
  ["helpdesk"]="74d165dfd1bd30c5603025386003909315638542"
  ["contract"]="f6f398760e075e0cb6e2f285f22d059b41a8826f"
  ["sign"]="3b768318bc5eaccb79535337478f49d59d17d0b1"
  ["field-service"]="561b1389636ac26e0a9fd86509302f51b733cb6c"
)

for repo in "${!PIN[@]}"; do
  sha="${PIN[$repo]}"
  if [ ! -d "$DEST/$repo/.git" ]; then
    echo "== clonando OCA/$repo =="
    git clone "https://github.com/OCA/$repo.git" "$DEST/$repo"
  fi
  echo "== $repo -> checkout $sha =="
  git -C "$DEST/$repo" fetch origin "$sha" 2>/dev/null || git -C "$DEST/$repo" fetch --all
  git -C "$DEST/$repo" checkout -q "$sha"
  got="$(git -C "$DEST/$repo" rev-parse HEAD)"
  [ "$got" = "$sha" ] || { echo "ERRO: $repo em $got, esperado $sha"; exit 1; }
done

echo "OK. Todos os OCA travados nos commits de dependencies.lock.yml."
echo "Ajuste o addons_path do Odoo para incluir cada repo em $DEST/ (ver docker/odoo.conf)."
