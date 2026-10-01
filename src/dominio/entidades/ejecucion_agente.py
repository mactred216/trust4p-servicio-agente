from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

ESTADOS_VALIDOS = {"exitosa", "fallida", "reintento"}


@dataclass
class EjecucionAgente:
    """RF-42/RF-43: bitácora de cada invocación al servicio de inferencia.
    Colección de solo anexado — se crea una vez por intento y nunca se
    modifica. R-13: 'peticion' guarda el contenido efectivamente enviado con
    los fragmentos truncados a un extracto; el contenido íntegro se
    recupera por los ids en fragmentos_recuperados.

    'reintento' marca un intento fallido que sí va a reintentarse;
    'fallida' marca el intento final que agota la política de reintentos."""

    id: Optional[str]
    diagnostico_id: str
    intento: int
    peticion: dict[str, Any]
    fragmentos_recuperados: list[str]
    proveedor: str
    modelo: str
    version_prompt: str
    modelo_version: str
    estado: str
    respuesta: Optional[dict[str, Any]] = None
    mensaje_error: Optional[str] = None
    tokens_entrada: Optional[int] = None
    tokens_salida: Optional[int] = None
    duracion_ms: Optional[int] = None
    ejecutado_en: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
