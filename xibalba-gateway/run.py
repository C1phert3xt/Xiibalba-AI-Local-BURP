# run.py
import uvicorn
from config import settings

if __name__ == "__main__":
    # host fijo desde config: 127.0.0.1 o IP de tailscale0. NUNCA 0.0.0.0.
    uvicorn.run(
        "gateway:app",
        host=settings.bind_host,
        port=settings.bind_port,
        workers=1,            # 1 worker: el semaforo de VRAM es por proceso
        access_log=False,     # la auditoria JSON reemplaza el log de acceso
    )
