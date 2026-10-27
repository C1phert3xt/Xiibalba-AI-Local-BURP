#!/usr/bin/env bash
# poc_smoke_test.sh — Valida los controles de seguridad del Xibalba Gateway.
# Prueba: salud, autenticación (sin/mal/buena clave), validación de esquema y
# rate limiting. No requiere GPU: los controles se evalúan ANTES de la inferencia.
#
# Uso:  XIBALBA_KEY="tu-clave" ./poc_smoke_test.sh [http://127.0.0.1:8000]
set -u

BASE="${2:-http://127.0.0.1:8000}"
KEY="${XIBALBA_KEY:?Exporta XIBALBA_KEY con una clave válida del gateway}"
PASS=0; FAIL=0

check() { # $1=descripción  $2=esperado  $3=obtenido
    if [[ "$2" == "$3" ]]; then echo "  [OK]   $1 (HTTP $3)"; ((PASS++))
    else echo "  [FALLA] $1 — esperado $2, obtenido $3"; ((FAIL++)); fi
}

code() { curl -s -o /dev/null -w "%{http_code}" "$@"; }

echo "== Xibalba Gateway — POC de controles de seguridad =="
echo "Objetivo: $BASE"
echo

echo "[1] Salud del servicio"
check "GET /health responde 200" 200 "$(code "$BASE/health")"
echo

echo "[2] Autenticación Bearer"
check "Sin token -> 401" 401 "$(code -X POST "$BASE/v1/chat/completions" \
    -H 'Content-Type: application/json' \
    -d '{"model":"qwen2.5-coder:latest","messages":[{"role":"user","content":"hola"}]}')"
check "Token inválido -> 401" 401 "$(code -X POST "$BASE/v1/chat/completions" \
    -H 'Authorization: Bearer clave-falsa-xyz' -H 'Content-Type: application/json' \
    -d '{"model":"qwen2.5-coder:latest","messages":[{"role":"user","content":"hola"}]}')"
echo

echo "[3] Validación de esquema (Pydantic extra=forbid)"
check "Campo no permitido -> 422" 422 "$(code -X POST "$BASE/v1/chat/completions" \
    -H "Authorization: Bearer $KEY" -H 'Content-Type: application/json' \
    -d '{"model":"qwen2.5-coder:latest","messages":[{"role":"user","content":"hola"}],"campo_malicioso":1}')"
check "messages vacío -> 422" 422 "$(code -X POST "$BASE/v1/chat/completions" \
    -H "Authorization: Bearer $KEY" -H 'Content-Type: application/json' \
    -d '{"model":"qwen2.5-coder:latest","messages":[]}')"
echo

echo "[4] Rate limiting (envía 40 peticiones; alguna debe dar 429)"
got429=0
for i in $(seq 1 40); do
    c=$(code -X POST "$BASE/v1/chat/completions" \
        -H "Authorization: Bearer $KEY" -H 'Content-Type: application/json' \
        -d '{"model":"qwen2.5-coder:latest","messages":[{"role":"user","content":"x"}]}')
    [[ "$c" == "429" ]] && got429=1 && break
done
check "Se dispara 429 bajo ráfaga" 1 "$got429"
echo

echo "== Resultado: $PASS OK, $FAIL fallas =="
[[ $FAIL -eq 0 ]] && echo "POC de seguridad: APROBADA" || { echo "POC de seguridad: REVISAR"; exit 1; }
