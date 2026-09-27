from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

CATEGORIAS_VALIDAS = {
    "rubrica",
    "dimensiones",
    "perfiles_cultura",
    "ejemplos",
    "marco_teorico",
}


@dataclass
class DocumentoConocimiento:
    """RF-41: documento de referencia que alimenta la base de conocimiento
    del agente. 'Actualizar' no sobreescribe el documento existente: crea
    uno nuevo con otra versión y desactiva el anterior, para conservar el
    historial de versiones anteriores tal como exige RF-41 paso 2."""

    id: Optional[str]
    titulo: str
    categoria: str
    version: str
    cargado_por: str
    fuente: Optional[str] = None
    activo: bool = True
    creado_en: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def desactivar(self) -> None:
        if not self.activo:
            raise ValueError("El documento ya se encuentra inactivo")
        self.activo = False

    def reactivar(self) -> None:
        if self.activo:
            raise ValueError("El documento ya se encuentra activo")
        self.activo = True
