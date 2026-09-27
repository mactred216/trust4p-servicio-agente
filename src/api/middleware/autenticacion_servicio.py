import os

from fastapi import Header, HTTPException


async def requiere_servicio_autorizado(
    x_api_key: str | None = Header(default=None),
) -> None:
    """ADR-001: comunicación entre servicios con autenticación propia,
    distinta de la cookie de sesión de usuario — este endpoint lo invoca
    trust4p-api-negocio, no un navegador. Secreto compartido simple,
    proporcional a la escala de un sistema de dos backends; no es la
    autenticación de usuarios finales."""
    clave_esperada = os.getenv("API_KEY_SERVICIOS")
    if not clave_esperada:
        raise HTTPException(
            status_code=500, detail="API_KEY_SERVICIOS no está configurada"
        )
    if x_api_key != clave_esperada:
        raise HTTPException(status_code=401, detail="No autorizado")
