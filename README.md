# Xibalba AI — Ecosistema de IA ofensiva 100% local

![Xibalba AI key-art](docs/assets/xibalba-keyart.png)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![Java](https://img.shields.io/badge/Java-21-orange.svg)

Análisis de seguridad web asistido por inteligencia artificial **100% local**,
sin fugas a la nube. Un gateway FastAPI compatible con OpenAI frente a tus
modelos locales (Ollama / vLLM) y una extensión de Burp Suite que envía el
tráfico interceptado a ese modelo para análisis de vulnerabilidades.

> **Uso autorizado únicamente.** Herramienta de seguridad ofensiva para pruebas
> bajo autorización explícita y laboratorios propios. Lee el
> [DISCLAIMER](DISCLAIMER.md) antes de usarla.

Dos componentes:

- `xibalba-gateway/` — Wrapper FastAPI compatible con OpenAI frente a Ollama/vLLM.
- `xibalba-burp/` — Extensión Burp Suite Pro (Montoya API) que analiza tráfico con el modelo local.

> **Entorno WSL2 Kali en Windows 11** (Ollama con `qwen2.5-coder:latest`): la
> topología de red host↔WSL2 se explica en [docs/WSL2_SETUP.md](docs/WSL2_SETUP.md).
> El gateway corre dentro de WSL2 junto a Ollama; Burp lo alcanza vía modo de red
> *mirrored*.

## 1. Gateway (FastAPI)

```bash
cd xibalba-gateway
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
chmod 600 .env
# Genera claves:  python3 -c "import secrets; print(secrets.token_urlsafe(32))"
# Edita .env con tus claves y el upstream (Ollama 11434 / vLLM 8001)
python3 run.py
```

**¿Primera vez? Prueba de concepto de extremo a extremo:** sigue
[docs/POC_RUNBOOK.md](docs/POC_RUNBOOK.md) y valida los controles con
`scripts/poc_smoke_test.sh`.

Controles implementados:
1. Autenticación Bearer (hashes SHA-256, comparación en tiempo constante) — `security.py`
2. Binding seguro + guard anti-SSRF (loopback / RFC1918 / Tailscale CGNAT; bloquea metadatos de nube 169.254.169.254) — `gateway.py`, `run.py`
3. Rate limiting por clave (slowapi) + semáforo de concurrencia para proteger la VRAM — `gateway.py`
4. Validación Pydantic estricta del esquema OpenAI (`extra="forbid"`) — `schemas.py`

Endurecimiento de red (defensa en profundidad del binding):
```bash
sudo ufw deny 8000/tcp
sudo ufw allow in on lo to any port 8000 proto tcp
sudo ufw allow in on tailscale0 to any port 8000 proto tcp
```

Detección Purple Team: `detections/sigma_ai_gateway_abuse.yml`

### Prueba rápida
```bash
curl -s http://127.0.0.1:8000/v1/chat/completions \
  -H "Authorization: Bearer TU_CLAVE" -H "Content-Type: application/json" \
  -d '{"model":"qwen2.5-coder:32b","messages":[{"role":"user","content":"ping"}]}'
```

## 2. Extensión Burp (Montoya API, Java 21)

```bash
cd xibalba-burp
export XIBALBA_AI_KEY="la-misma-clave-que-pusiste-en-el-gateway"
./gradlew shadowJar          # -> build/libs/xibalba-burp-*-all.jar
```
En Burp: Extensions → Add → Java → selecciona el `-all.jar`.
Arranca Burp desde la misma shell donde exportaste `XIBALBA_AI_KEY` para que la vea.

Uso: clic derecho sobre un request en Proxy/Repeater → "Analizar con IA local (Xibalba)".
Los hallazgos aparecen en Dashboard → Issues, marcados `[IA]` y con confianza TENTATIVE.

## Nota de seguridad del pipeline
El `response` del objetivo es contenido no confiable que se envía al modelo (riesgo de
inyección de prompt indirecta). Mitigaciones: delimitadores `<<<TRAFICO>>>`, declaración
de "datos no instrucciones" en el system prompt, `temperature 0.1`, escape HTML de la
salida del modelo, y validación manual del analista — nunca acción automática sobre un hallazgo.

## Licencia

Distribuido bajo licencia [MIT](LICENSE). Consulta también el
[DISCLAIMER](DISCLAIMER.md) y la [política de seguridad](SECURITY.md).
