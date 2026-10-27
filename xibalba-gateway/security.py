# security.py
# Dependencia de autenticación. Comparación en tiempo constante contra
# el conjunto de hashes; no se revela si la clave existe o solo es incorrecta.
import hashlib
import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from config import settings

_bearer = HTTPBearer(auto_error=False)


def hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


async def require_api_key(
    creds: HTTPAuthorizationCredentials = Depends(_bearer),
) -> str:
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Falta token Bearer",
            headers={"WWW-Authenticate": "Bearer"},
        )
    presented = hash_key(creds.credentials)
    valido = any(secrets.compare_digest(presented, h) for h in settings.api_key_hashes)
    if not valido:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API Key inválida")
    return presented[:12]   # identificador de clave para auditoría/limitador
