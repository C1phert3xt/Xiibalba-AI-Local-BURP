# Política de seguridad

## Reporte de vulnerabilidades

Si encuentras una vulnerabilidad en este proyecto, repórtala de forma privada
antes de divulgarla públicamente:

- Abre un *Security Advisory* privado en GitHub (pestaña **Security** →
  *Report a vulnerability*), o
- Contacta al mantenedor por canal privado.

Por favor **no** abras un *issue* público para vulnerabilidades sin parche.

## Alcance

Este repositorio contiene herramientas de seguridad ofensiva. Los reportes de
seguridad que nos interesan son defectos en el **propio software** (por ejemplo:
el gateway expone tráfico por un binding inseguro, una omisión de la validación
de autenticación, o una fuga de la clave de API), no el hecho de que la
herramienta pueda usarse para analizar otros sistemas — ese es su propósito.

## Buenas prácticas al operar el gateway

- Mantén el *binding* en `127.0.0.1` o en la interfaz de gestión (Tailscale/VLAN).
- Rota las claves de API y usa una por consumidor.
- Nunca subas tu `.env` real al repositorio (ya está en `.gitignore`).
- Pasa `gitleaks` antes de cada publicación.
