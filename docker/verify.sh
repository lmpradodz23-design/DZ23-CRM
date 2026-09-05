#!/usr/bin/env bash
# Verificação automática do rebrand DZ23 CRM.
# Uso: bash verify.sh  (requer Docker rodando e a stack de pé)
set -u
BASE="http://localhost:8069"
pass=0; fail=0
check() { # $1=descrição  $2=comando que retorna 0/1
  if eval "$2" >/dev/null 2>&1; then echo "  [OK]   $1"; pass=$((pass+1));
  else echo "  [FALHA] $1"; fail=$((fail+1)); fi
}

echo "== Subindo stack =="
docker compose up -d
echo "== Inicializando base + módulos (primeira vez pode demorar) =="
docker compose run --rm odoo odoo -d dz23crm \
  -i base,dz23_branding,dz23_brasil_tools,dz23_crm,dz23_whatsapp \
  --load-language=pt_BR --stop-after-init || true
docker compose up -d
echo "== Aguardando Odoo responder =="
for i in $(seq 1 30); do curl -sf "$BASE/web/login" >/dev/null 2>&1 && break; sleep 3; done

echo "== Checagens de debrand =="
LOGIN=$(curl -s "$BASE/web/login")
MANIFEST=$(curl -s "$BASE/web/manifest.webmanifest")

check "Login NÃO contém 'Powered by Odoo'"        "! grep -qi 'Powered by <span>Odoo' <<< \"\$LOGIN\""
check "Login referencia favicon DZ23"             "grep -q 'dz23_branding/static/src/img/favicon' <<< \"\$LOGIN\""
check "Título da página é DZ23 CRM"               "grep -qi '<title>DZ23 CRM' <<< \"\$LOGIN\""
check "Manifest PWA name = DZ23 CRM"              "grep -q '\"name\": *\"DZ23 CRM\"' <<< \"\$MANIFEST\""
check "Manifest theme_color navy #003175"         "grep -qi '#003175' <<< \"\$MANIFEST\""
check "Manifest usa ícone DZ23"                   "grep -q 'dz23_branding/static/src/img/icon-' <<< \"\$MANIFEST\""

echo "== Resultado: $pass OK / $fail falhas =="
exit $fail
