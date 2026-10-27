# gateway.py
import asyncio
import json
import logging
import socket
import sys
from contextlib import asynccontextmanager
from ipaddress import ip_address, ip_network
from urllib.parse import urlparse

# Rango CGNAT que usa Tailscale (100.64.0.0/10). NO es is_private en Python,
# por eso se incluye como red de gestion permitida de forma explicita.
_TAILSCALE_CGNAT = ip_network("100.64.0.0/10")

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse, StreamingResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded

from config import settings
from schemas import ChatCompletionRequest
from security import hash_key, require_api_key

# --- Auditoría estructurada (JSON Lines -> consumible por Sentinel/Sigma) ---
logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(message)s")
log = logging.getLogger("xibalba.gateway")


def audit(event: str, **fields) -> None:
    log.info(json.dumps({"source": "xibalba-ai-gateway", "event": event, **fields}))


# --- Guarda anti-SSRF: el upstream es fijo y debe resolver a loopback/privado ---
def validate_upstream(url: str) -> None:
    host = urlparse(url).hostname
    for *_, sockaddr in socket.getaddrinfo(host, None):
        ip = ip_address(sockaddr[0])
        # Link-local (169.254.0.0/16) = endpoint de metadatos de nube (169.254.169.254).
        # Python lo marca is_private, asi que se rechaza ANTES de la lista blanca.
        if ip.is_link_local:
            raise RuntimeError(
                f"OPSEC: upstream {host} resuelve a link-local {ip} (metadatos de nube). Bloqueado."
            )
        # Se permite loopback, rango privado (RFC1918) o CGNAT de Tailscale.
        if not (ip.is_loopback or ip.is_private or ip in _TAILSCALE_CGNAT):
            raise RuntimeError(
                f"OPSEC: upstream {host} resuelve a {ip} (no loopback/privado). Bloqueado."
            )


# --- Limitador de peticiones por clave (no por IP: todo viene de localhost) ---
def api_key_identity(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return hash_key(auth[7:])[:12]
    return "anon"


limiter = Limiter(key_func=api_key_identity, default_limits=[settings.rate_limit])

# --- Semaforo global: limita inferencias SIMULTANEAS para proteger la VRAM.
#     El rate limit controla frecuencia; el semaforo controla carga concurrente. ---
inference_slots = asyncio.Semaphore(settings.max_concurrency)


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_upstream(settings.upstream_base_url)
    app.state.client = httpx.AsyncClient(
        base_url=settings.upstream_base_url,
        timeout=httpx.Timeout(settings.upstream_timeout, connect=5.0),
        trust_env=False,  # OPSEC: ignora HTTP(S)_PROXY del entorno; sin egress accidental
        limits=httpx.Limits(max_connections=settings.max_concurrency * 2),
    )
    audit("startup", upstream=settings.upstream_base_url, bind=settings.bind_host)
    yield
    await app.state.client.aclose()


app = FastAPI(title="Xibalba AI Gateway", lifespan=lifespan, docs_url=None, redoc_url=None)
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def _rate_limited(request: Request, exc: RateLimitExceeded):
    audit("rate_limited", key=api_key_identity(request))
    return JSONResponse(status_code=429, content={"error": "Limite de peticiones excedido"})


# Emite auth_failure para la regla Sigma cuando la autenticacion Bearer falla.
@app.exception_handler(HTTPException)
async def _http_exc(request: Request, exc: HTTPException):
    if exc.status_code == status.HTTP_401_UNAUTHORIZED:
        audit("auth_failure", key=api_key_identity(request), path=request.url.path)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail},
        headers=getattr(exc, "headers", None),
    )


# --- Middleware: corta cuerpos excesivos antes de leerlos completos ---
@app.middleware("http")
async def limit_body_size(request: Request, call_next):
    cl = request.headers.get("content-length")
    if cl and cl.isdigit() and int(cl) > settings.max_body_bytes:
        return JSONResponse(status_code=413, content={"error": "Payload demasiado grande"})
    return await call_next(request)


@app.get("/health")
async def health():
    return {"status": "ok"}


async def _stream_upstream(client, body, headers, key_id, model):
    # El semaforo se mantiene toda la vida del stream: ese slot de VRAM esta ocupado.
    async with inference_slots:
        audit("inference", key=key_id, model=model, mode="stream")
        async with client.stream("POST", "/chat/completions", json=body, headers=headers) as r:
            async for chunk in r.aiter_raw():
                yield chunk


@app.post("/v1/chat/completions")
@limiter.limit(settings.rate_limit)
async def chat_completions(
    request: Request,
    payload: ChatCompletionRequest,
    key_id: str = Depends(require_api_key),
):
    # Lista blanca de modelos
    if settings.allowed_models and payload.model not in settings.allowed_models:
        audit("model_denied", key=key_id, model=payload.model)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Modelo no permitido: {payload.model}")

    # Re-serializa SOLO desde el modelo validado: descarta cualquier residuo del raw body.
    body = payload.model_dump(exclude_none=True)
    headers = {"Content-Type": "application/json"}
    if settings.upstream_api_key:
        headers["Authorization"] = f"Bearer {settings.upstream_api_key}"

    client: httpx.AsyncClient = request.app.state.client

    if payload.stream:
        return StreamingResponse(
            _stream_upstream(client, body, headers, key_id, payload.model),
            media_type="text/event-stream",
        )

    async with inference_slots:
        audit("inference", key=key_id, model=payload.model, mode="sync")
        r = await client.post("/chat/completions", json=body, headers=headers)
    return JSONResponse(status_code=r.status_code, content=r.json())
