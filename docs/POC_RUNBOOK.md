# Runbook de Prueba de Concepto — Xibalba AI

Validación de extremo a extremo del ecosistema: Ollama → Gateway → Burp Suite.
Entorno: WSL2 Kali en Windows 11, Ollama con `qwen2.5-coder:latest`.

Cada paso tiene un **resultado esperado**. Si no coincide, mira la nota "Falla si".

---

## Fase 0 — Pre-requisitos (WSL2 Kali)

```bash
# Modelo disponible
ollama list
# Esperado: aparece  qwen2.5-coder:latest

# Ollama responde
curl -s http://127.0.0.1:11434/v1/models | python3 -m json.tool | head
# Esperado: JSON con el modelo listado
```

**Falla si** `ollama list` no muestra el modelo → `ollama pull qwen2.5-coder:latest`.
**Falla si** el `curl` no responde → arranca el servicio: `ollama serve &`.

---

## Fase 1 — Arrancar el Gateway

```bash
cd ~/xibalba/xibalba-gateway        # o /mnt/c/Xibalba/xibalba-gateway
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env && chmod 600 .env
# Genera una clave real y ponla en XIBALBA_API_KEYS:
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
nano .env     # pega la clave; confirma modelo qwen2.5-coder:latest

python3 run.py
```

**Resultado esperado:** en consola aparece
`{"source": "xibalba-ai-gateway", "event": "startup", ...}` y
`Uvicorn running on http://127.0.0.1:8000`.

**Falla si** lanza `RuntimeError: OPSEC: upstream ... Bloqueado` → el upstream del
`.env` no resuelve a loopback/privado; revísalo.

---

## Fase 2 — Validar los controles de seguridad (automático)

En **otra terminal** de WSL2, con el gateway corriendo:

```bash
cd ~/xibalba
export XIBALBA_KEY="la-clave-que-pusiste-en-.env"
bash scripts/poc_smoke_test.sh
```

**Resultado esperado:**
```
[1] Salud ............... [OK] 200
[2] Sin token ........... [OK] 401
    Token inválido ...... [OK] 401
[3] Campo no permitido .. [OK] 422
    messages vacío ...... [OK] 422
[4] Rate limiting ....... [OK] 429
== Resultado: 6 OK, 0 fallas ==
POC de seguridad: APROBADA
```

Esto prueba, sin gastar GPU: autenticación Bearer, validación estricta de
esquema (Pydantic `extra=forbid`) y rate limiting por clave.

**Falla si** el paso 4 no da 429 → baja `XIBALBA_RATE_LIMIT` (ej. `"10/minute"`)
y reinicia el gateway para la prueba.

---

## Fase 3 — Prueba funcional de inferencia (usa GPU)

```bash
curl -s http://127.0.0.1:8000/v1/chat/completions \
  -H "Authorization: Bearer $XIBALBA_KEY" -H "Content-Type: application/json" \
  -d '{"model":"qwen2.5-coder:latest","messages":[{"role":"user","content":"Responde solo: OK"}]}' \
  | python3 -m json.tool
```

**Resultado esperado:** JSON con `choices[0].message.content` conteniendo la
respuesta del modelo. En la consola del gateway ves un evento
`"event": "inference", ..., "mode": "sync"`.

**Falla si** tarda demasiado o da 500 → confirma que Ollama tiene el modelo
cargado (`ollama ps`) y que hay VRAM libre.

---

## Fase 4 — Compilar la extensión de Burp

En WSL2 (necesitas JDK 21):

```bash
java -version      # debe ser 21; si no:  sudo apt install openjdk-21-jdk
cd ~/xibalba/xibalba-burp
./gradlew shadowJar
# Esperado: BUILD SUCCESSFUL, genera build/libs/xibalba-burp-*-all.jar
```

**Falla si** Gradle no encuentra la API Montoya → ajusta la versión en
`build.gradle` a la que muestra Burp en *Extensions → APIs*.

---

## Fase 5 — Cargar la extensión en Burp (Windows)

El `.jar` compilado en WSL está accesible desde Windows en
`\\wsl$\kali-linux\home\<usuario>\xibalba\xibalba-burp\build\libs\`.

1. Exporta la clave y arranca Burp **desde la misma consola** para que la vea:
   - PowerShell: `$env:XIBALBA_AI_KEY="la-misma-clave-del-gateway"; & "C:\Program Files\BurpSuitePro\BurpSuitePro.exe"`
2. Burp → **Extensions → Add → Java** → selecciona el `-all.jar`.

**Resultado esperado:** en la pestaña *Output* de la extensión aparece
`[Xibalba] AI Analyzer cargado.`

**Falla si** dice `Falta la variable de entorno XIBALBA_AI_KEY` → no arrancaste
Burp desde la consola con la variable exportada.

---

## Fase 6 — Objetivo vulnerable para la prueba

Levanta un objetivo deliberadamente vulnerable (no pruebes contra terceros):

```bash
# OWASP Juice Shop en Docker (dentro de WSL2)
docker run --rm -p 3000:3000 bkimminich/juice-shop
# Objetivo:  http://127.0.0.1:3000
```

Configura el navegador para usar el proxy de Burp (127.0.0.1:8080) y navega el
objetivo para capturar tráfico en el Proxy.

---

## Fase 7 — Prueba del pipeline completo (el corazón de la POC)

1. En Burp, ve a **Proxy → HTTP history** (o **Repeater**).
2. Clic derecho sobre un request con parámetros interesantes (ej. una petición a
   `/rest/user/...` o un `id=` en la URL) → **"Analizar con IA local (Xibalba)"**.
3. Observa la consola del gateway: debe aparecer un evento `"event": "inference"`.

**Resultado esperado — la cadena completa funciona:**
Burp empaqueta el tráfico en JSON OpenAI → lo manda al gateway → el gateway
autentica, valida y reenvía a Ollama → el modelo responde → la extensión parsea
el JSON y registra el hallazgo.

4. Ve a **Dashboard → Issues** (o **Target → Site map**).

**Resultado esperado:** aparece uno o más issues marcados `[IA] ...`, con
severidad, confianza `TENTATIVE` y el request/response adjunto como evidencia.

**Falla si** no aparece el issue pero sí hubo `inference` en el gateway → revisa
la pestaña *Errors* de la extensión; lo más común es que el modelo no devolvió un
arreglo JSON válido (sube un modelo más capaz o baja `temperature`).

---

## Checklist de aceptación de la POC

- [ ] Fase 0: Ollama sirve `qwen2.5-coder:latest`
- [ ] Fase 2: `poc_smoke_test.sh` → 6 OK, 0 fallas
- [ ] Fase 3: una inferencia real devuelve contenido del modelo
- [ ] Fase 4: la extensión compila (`BUILD SUCCESSFUL`)
- [ ] Fase 5: Burp carga la extensión y lee la clave del entorno
- [ ] Fase 7: un hallazgo `[IA]` aparece en el Dashboard de Burp

Con las seis casillas marcadas, el ecosistema está probado de extremo a extremo.

---

## Nota de seguridad del pipeline (recordatorio)

El `response` del objetivo es contenido **no confiable** que se envía al modelo:
riesgo de inyección de prompt indirecta. La extensión ya mitiga con delimitadores,
declaración de "datos no instrucciones", `temperature` baja y escape HTML. Regla
operativa: **ningún hallazgo `[IA]` se reporta al cliente sin validación manual.**
