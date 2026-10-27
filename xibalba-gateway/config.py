# config.py
# Configuración central del Gateway. Los secretos se cargan desde .env
# (permisos 600) y las API Keys nunca se mantienen en texto plano en memoria:
# se almacenan como hashes SHA-256 para comparación en tiempo constante.
import hashlib
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="XIBALBA_", env_file=".env")

    # --- Binding seguro ---
    bind_host: str = "127.0.0.1"          # o la IP de tu interfaz Tailscale/VLAN
    bind_port: int = 8000

    # --- Motor de inferencia (upstream fijo, no controlable por el cliente) ---
    upstream_base_url: str = "http://127.0.0.1:11434/v1"   # Ollama; vLLM: :8001/v1
    upstream_api_key: str | None = None    # si vLLM exige --api-key

    # --- Autenticación ---
    # Coma-separada en .env. Se hashea al arrancar; se recomienda rotarlas.
    api_keys: str = ""

    # --- Control de recursos ---
    allowed_models: list[str] = []         # lista blanca; vacío = sin filtro
    rate_limit: str = "30/minute"          # peticiones por clave
    max_concurrency: int = 2               # inferencias simultáneas (guarda la VRAM)
    max_body_bytes: int = 1_048_576        # 1 MiB; corta payloads abusivos
    upstream_timeout: float = 120.0

    @property
    def api_key_hashes(self) -> frozenset[str]:
        return frozenset(
            hashlib.sha256(k.strip().encode()).hexdigest()
            for k in self.api_keys.split(",")
            if k.strip()
        )


settings = Settings()
