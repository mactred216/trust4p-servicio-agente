from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class FragmentoConocimiento:
    """RF-42/ASR-15: fragmento vectorizado de un documento de la base de
    conocimiento. Colección independiente del documento porque requiere su
    propio índice vectorial (búsqueda por similitud)."""

    id: Optional[str]
    documento_id: str
    categoria: str
    orden: int
    contenido: str
    embedding: list[float]
    tokens: Optional[int] = None
    activo: bool = True
    creado_en: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def desactivar(self) -> None:
        if not self.activo:
            raise ValueError("El fragmento ya se encuentra inactivo")
        self.activo = False

    def reactivar(self) -> None:
        if self.activo:
            raise ValueError("El fragmento ya se encuentra activo")
        self.activo = True
