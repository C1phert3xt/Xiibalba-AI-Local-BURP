# Guía de publicación en GitHub — Xibalba AI

Paso a paso para versionar y subir el repositorio `xibalba` a GitHub, con las
precauciones de OPSEC necesarias (ninguna clave ni `.env` debe salir del host).

---

## 0. Pre-requisitos (una sola vez)

```bash
# Git instalado
git --version

# Identidad local (si aún no la tienes)
git config --global user.name "Luis Fajardo"
git config --global user.email "6luiscarret@gmail.com"

# GitHub CLI (recomendado para crear el repo sin salir de la terminal)
gh --version || sudo apt install gh    # Debian/Ubuntu
gh auth login                          # elige GitHub.com -> HTTPS -> navegador
```

---

## 1. Verificar que NO se suben secretos

El `.gitignore` ya excluye `.env`, `build/`, `.venv/` y `__pycache__/`.
Confirma que tu `.env` real existe solo localmente y está ignorado:

```bash
cd xibalba
cat .gitignore
# Debe listar: .env

# Verificación dura: que git NO vea el .env
git status --ignored 2>/dev/null | grep -i "\.env$" || echo "revisar .gitignore"
```

> Regla OPSEC: solo se versiona `.env.example` (plantilla sin claves).
> Si alguna vez un `.env` real llega al índice, deténte y sácalo antes de commitear:
> `git rm --cached xibalba-gateway/.env`

---

## 2. Inicializar el repositorio local

```bash
cd xibalba
git init
git branch -M main
git add .
git status          # revisa la lista: NO debe aparecer ningún .env
```

---

## 3. Primer commit

```bash
git commit -m "Initial commit: Xibalba AI gateway (FastAPI) + Burp extension (Montoya)

- Wrapper OpenAI-compatible con auth Bearer, guard anti-SSRF, rate limiting
  por clave y validación Pydantic estricta.
- Extensión Burp Suite (Montoya API) que analiza tráfico con el modelo local
  y registra hallazgos en el Issue Tracker.
- Regla Sigma de detección para abuso del gateway.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01Aoz1d74hT1EoVVx2FiLVjL"
```

---

## 4. Autenticarse en GitHub (una sola vez)

Si `gh` responde `HTTP 401: Bad credentials`, falta autenticación:

```bash
gh auth login
# GitHub.com -> HTTPS -> Yes (autenticar git) -> Login with a web browser
gh auth status      # debe decir: Logged in to github.com as <usuario>
```

## 5. Crear el repositorio remoto y subir (PÚBLICO)

```bash
gh repo create xibalba-ai --public --source=. --remote=origin --push \
  --description "Ecosistema de IA ofensiva 100% local: gateway FastAPI compatible con OpenAI y extensión de Burp Suite (Montoya API) para análisis de tráfico con modelos locales."
```

Luego agrega los topics para que sea descubrible:

```bash
gh repo edit --add-topic offensive-security,pentesting,burp-suite,fastapi,local-llm,ollama,purple-team,appsec,montoya-api
```

> Repo PÚBLICO: el escaneo de secretos (paso 8) deja de ser opcional. Córrelo
> ANTES del push — una vez publicado, un secreto filtrado ya fue indexado.

### Alternativa manual (si creaste el repo en la web de GitHub)

```bash
# Crea el repo vacío en github.com (sin README, sin .gitignore, sin licencia)
git remote add origin git@github.com:TU_USUARIO/xibalba-ai.git   # SSH
# o HTTPS:  git remote add origin https://github.com/TU_USUARIO/xibalba-ai.git
git push -u origin main
```

> SSH vs HTTPS: para empujes frecuentes, SSH evita pedir credenciales.
> Genera clave si no tienes: `ssh-keygen -t ed25519 -C "6luiscarret@gmail.com"`
> y súbela en GitHub → Settings → SSH and GPG keys.

---

## 6. Licencia y avisos legales

El repo ya incluye, en la raíz:

- `LICENSE` — MIT. GitHub la detecta sola y muestra la etiqueta de licencia.
- `DISCLAIMER.md` — uso autorizado únicamente; deslinde de responsabilidad y
  nota de marca sobre Burp Suite® (PortSwigger).
- `SECURITY.md` — cómo reportar vulnerabilidades del propio software (GitHub lo
  enlaza desde la pestaña *Security*).

Si prefieres Apache 2.0 en vez de MIT, reemplaza `LICENSE` y actualiza la
insignia del `README.md`.

---

## 7. Flujo de trabajo para cambios posteriores

Cada mejora (p. ej. el modo `HttpHandler` pasivo o el enrutamiento multi-modelo)
va en su propia rama, con Pull Request:

```bash
git checkout -b feat/passive-httphandler
# ...editas código...
git add .
git commit -m "feat(burp): escaneo pasivo automático vía HttpHandler

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01Aoz1d74hT1EoVVx2FiLVjL"
git push -u origin feat/passive-httphandler

# Abre el PR
gh pr create --fill
```

---

## 8. Red de seguridad: escaneo de secretos

Antes de hacer público cualquier repo de seguridad, pasa un detector de secretos:

```bash
# gitleaks: escanea todo el historial, no solo el estado actual
docker run --rm -v "$(pwd):/repo" zricethezav/gitleaks:latest detect --source=/repo -v
```

Si gitleaks encuentra algo ya commiteado, no basta con borrarlo en un commit nuevo:
hay que reescribir el historial (`git filter-repo`) y **rotar la clave expuesta**.

---

## 9. (Opcional) Protección de rama y plantilla de PR

```bash
# Requiere revisión antes de merge a main (si trabajas con tu equipo)
gh api repos/TU_USUARIO/xibalba-ai/branches/main/protection -X PUT \
  -H "Accept: application/vnd.github+json" \
  -f required_pull_request_reviews.required_approving_review_count=1 \
  -F enforce_admins=true 2>/dev/null || echo "configúralo desde Settings -> Branches"
```

Plantilla de PR en `.github/pull_request_template.md` (ver archivo adjunto en el repo).

---

## 10. Imagen de marca (key-art)

El banner oficial vive en el repo en:

```
docs/assets/xibalba-keyart.png
```

Ya está referenciado al tope del `README.md` con:

```markdown
![Xibalba AI key-art](docs/assets/xibalba-keyart.png)
```

GitHub lo renderiza automáticamente al abrir el repositorio. Notas:

- La ruta es **relativa** (`docs/assets/...`), así funciona igual en GitHub,
  en un clon local y en un fork, sin URLs absolutas que se rompan.
- Es un binario (PNG ~2.4 MB). Un solo asset de marca por `git` normal está
  bien; si a futuro acumulas muchas imágenes/vídeos pesados, migra esa carpeta
  a **Git LFS** (`git lfs track "*.png"`) para no inflar el historial.
- Si regeneras el arte, reemplaza el archivo con el **mismo nombre** y haz
  commit: el README seguirá apuntando correcto sin tocar el Markdown.

```bash
git add docs/assets/xibalba-keyart.png README.md
git commit -m "docs: add Xibalba key-art banner to README

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01Aoz1d74hT1EoVVx2FiLVjL"
```
