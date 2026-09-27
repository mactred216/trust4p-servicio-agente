from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

ESTADOS_VALIDOS = {"exitosa", "fallida"}


@dataclass
class EjecucionAgente:
    """RF-42/RF-43: bitácora de cada invocación al servicio de inferencia.
    Colección de solo anexado — se crea una vez por intento y nunca se
    modifica. R-13: 'peticion' guarda el contenido efectivamente enviado con
    los fragmentos truncados a un extracto; el contenido íntegro se
    recupera por los ids en fragmentos_recuperados."""

    id: Optional[str]
    diagnostico_id: str
    intento: int
    peticion: dict[str, Any]
    fragmentos_recuperados: list[str]
    modelo_lenguaje_id: str
    version_plantilla_instrucciones: str
    estado: str
    respuesta: Optional[dict[str, Any]] = None
    motivo_fallo: Optional[str] = None
    creado_en: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
