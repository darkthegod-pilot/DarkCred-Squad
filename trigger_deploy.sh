#!/bin/bash
# trigger_deploy.sh — Aciona auto-deploy no VPS após git push
# Claude usa este script automaticamente após cada commit+push

set -euo pipefail

ENV_FILE="$(dirname "$0")/.env"
[[ -f "$ENV_FILE" ]] && source "$ENV_FILE"

URL="${WEBHOOK_URL:-http://187.77.242.86:8000/webhook/push}"
SECRET="${WEBHOOK_SECRET:-}"

if [[ -z "$SECRET" ]]; then
  echo "⚠  WEBHOOK_SECRET não definido em .env — adicione WEBHOOK_SECRET=..."
  exit 1
fi

echo "→ Acionando deploy no VPS..."

RESPONSE=$(curl -s -w "\n%{http_code}" \
  -X POST "$URL" \
  -H "X-Webhook-Secret: $SECRET" \
  -H "Content-Type: application/json" \
  -d '{"ref":"refs/heads/claude/darkcred-instagram-merchants-xHC03"}' \
  --max-time 10)

HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -1)

if [[ "$HTTP_CODE" == "200" ]]; then
  echo "✅ Deploy acionado — VPS atualizando código e reiniciando..."
  echo "   $BODY"
else
  echo "❌ Falha no deploy (HTTP $HTTP_CODE): $BODY"
  exit 1
fi
