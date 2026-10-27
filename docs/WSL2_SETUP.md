# Despliegue en WSL2 Kali (Windows 11) con Ollama

Topología real del entorno:

```
┌─ Windows 11 (host) ────────────────────────────────────────────┐
│                                                                 │
│   Burp Suite Pro  ──► 127.0.0.1:8000 ──┐                        │
│   (extensión Montoya)                  │  cruce host <-> WSL2   │
│                                        ▼                        │
│   ┌─ WSL2 Kali (namespace de red propio) ─────────────────┐     │
│   │                                                        │     │
│   │   Xibalba Gateway (FastAPI)  127.0.0.1:8000            │     │
│   │            │                                           │     │
│   │            ▼                                           │     │
│   │   Ollama   127.0.0.1:11434   (qwen2.5-coder:latest)    │     │
│   │            │                                           │     │
│   │            ▼  GPU vía WSL                               │     │
│   └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
```

**Decisión de arquitectura:** el gateway corre **dentro de WSL2**, junto a Ollama.
Así el salto gateway → Ollama es loopback puro (`127.0.0.1:11434`) y el guard
anti-SSRF se cumple sin excepciones. El único cruce de frontera es Burp (Windows)
→ gateway (WSL2), y eso se resuelve con el modo de red de WSL, no abriendo puertos.

---

## Paso 1 — Verificar Ollama en WSL2 Kali

```bash
# Dentro de WSL2 Kali
ollama list                       # confirma: qwen2.5-coder:latest
curl -s http://127.0.0.1:11434/v1/models | head
```

Ollama por defecto escucha en `127.0.0.1:11434` dentro de WSL2. **No** cambies
`OLLAMA_HOST` a `0.0.0.0`: no hace falta y expondría el modelo a toda la red de WSL.

---

## Paso 2 — Red host <-> WSL2: usa modo "mirrored" (recomendado)

Windows 11 + WSL 2.0+ soportan **networkingMode=mirrored**, que hace que
`127.0.0.1` sea compartido entre Windows y WSL2. Con esto, el gateway bindea a
`127.0.0.1` dentro de WSL y Burp lo alcanza en `127.0.0.1:8000` sin exponer nada
a la LAN física. Es la opción más segura.

En Windows, edita `C:\Users\<tu-usuario>\.wslconfig`:

```ini
[wsl2]
networkingMode=mirrored
```

Luego, en PowerShell:

```powershell
wsl --shutdown
```

Reabre Kali. Verifica la versión (necesitas WSL 2.0.0 o superior):

```powershell
wsl --version
```

> Si `wsl --version` es anterior a 2.0.0:  `wsl --update`

---

## Paso 3 — Arrancar el gateway dentro de WSL2

```bash
# Dentro de WSL2 Kali, en la carpeta del repo
cd /mnt/c/Xibalba/xibalba-gateway       # o clónalo dentro del filesystem de WSL
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env && chmod 600 .env
# Edita .env: pon tus claves y confirma el modelo qwen2.5-coder:latest
python3 run.py
```

Con modo mirrored, `XIBALBA_BIND_HOST="127.0.0.1"` (el valor por defecto) es
correcto y suficiente.

> Rendimiento: trabaja el repo dentro del filesystem de Linux (`~/xibalba`), no
> en `/mnt/c/...`. El acceso a disco cruzando a NTFS es notablemente más lento.

---

## Paso 4 — Verificar el cruce desde Windows

Desde PowerShell en Windows (con el gateway corriendo en WSL):

```powershell
curl http://127.0.0.1:8000/health
# -> {"status":"ok"}

curl http://127.0.0.1:8000/v1/chat/completions `
  -H "Authorization: Bearer TU_CLAVE" -H "Content-Type: application/json" `
  -d '{\"model\":\"qwen2.5-coder:latest\",\"messages\":[{\"role\":\"user\",\"content\":\"ping\"}]}'
```

Si responde, Burp (que apunta a `http://127.0.0.1:8000`) ya funciona sin tocar
nada más.

---

## Alternativa — Modo NAT (si no puedes usar mirrored)

En el modo NAT clásico, `127.0.0.1` **no** es compartido. Dos caminos:

1. **localhostForwarding** (en `.wslconfig`):
   ```ini
   [wsl2]
   localhostForwarding=true
   ```
   Requiere que el proceso en WSL bindee a `0.0.0.0`. Es decir, arranca el
   gateway con `XIBALBA_BIND_HOST="0.0.0.0"`. El `0.0.0.0` aquí solo expone sobre
   la interfaz virtual de WSL (detrás del NAT), no sobre tu tarjeta física —
   pero es menos limpio que mirrored. Protege con el firewall de WSL:
   ```bash
   # dentro de WSL2
   sudo iptables -A INPUT -p tcp --dport 8000 -s 127.0.0.1 -j ACCEPT
   sudo iptables -A INPUT -p tcp --dport 8000 -j DROP
   ```

2. **IP directa de WSL:** `hostname -I` dentro de WSL da su IP `172.x` (RFC1918,
   permitida por el guard). Burp apunta a `http://172.x:8000`. Inconveniente: esa
   IP cambia en cada reinicio de WSL.

**Recomendación:** usa mirrored. Elimina el `0.0.0.0` y la IP cambiante.

---

## Nota sobre el guard anti-SSRF y la IP de WSL

Si algún día mueves el gateway al **host Windows** y apuntas el upstream a Ollama
en la IP de WSL (`172.x`), el guard lo permite porque `172.16.0.0/12` es RFC1918.
No necesitas tocar `validate_upstream()`. Pero la topología recomendada (gateway
en WSL) evita ese salto por completo.
