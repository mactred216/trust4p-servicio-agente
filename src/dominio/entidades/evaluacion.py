from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

# RF-14/RF-16 (Bloque D, Tabla 19 del documento de arquitectura): el agente
# nunca decide QUÉ perfil ni QUÉ recomendaciones aplican — solo redacta,
# a partir de lo que el motor de cálculo de trust4p-api-negocio ya
# determinó. Estas entidades reflejan ese contrato de entrada.


@dataclass
class DimensionCalculada:
    codigo: str
    puntaje: Decimal


@dataclass
class PerfilCulturalCalculado:
    codigo: str


@dataclass
class ResultadoCalculo:
    """Lo que trust4p-api-negocio ya calculó, de forma determinística,
    antes de invocar a este servicio (ADR-005)."""

    indice_global: Decimal
    nivel: int
    nivel_nombre: str
    nivel_descripcion: str
    dimensiones: list[DimensionCalculada]
    perfil_cultural: PerfilCulturalCalculado


@dataclass
class RespuestaDiagnostico:
    pregunta_codigo: str
    dimension_codigo: str
    enunciado: str
    tipo: str
    opciones_codigo: list[str] = field(default_factory=list)
    valor: Optional[Decimal] = None
    texto: Optional[str] = None


@dataclass
class DimensionModelo:
    codigo: str
    nombre: str
    peso: Decimal
    orden: int


@dataclass
class NivelModelo:
    nivel: int
    nombre: str
    descripcion: str
    umbral_min: Decimal
    umbral_max: Decimal


@dataclass
class SolicitudEvaluacion:
    """RF-36/Tabla 13: los tres bloques que componen la petición al agente,
    ya reunidos por trust4p-api-negocio. Deliberadamente no incluye razón
    social, NIT ni datos personales del representante — el identificador de
    empresa es un id opaco (RF-43), nunca la razón social."""

    diagnostico_id: str
    empresa_id: str
    modelo_version: str
    resultado_calculo: ResultadoCalculo
    respuestas: list[RespuestaDiagnostico]
    dimensiones_modelo: list[DimensionModelo]
    niveles_modelo: list[NivelModelo]


@dataclass
class RecomendacionAgente:
    dimension_codigo: str
    titulo: str
    contenido: str
    prioridad: int


@dataclass
class RespuestaAgente:
    """RF-37/Tabla 19: exactamente lo que el agente produce — interpretación,
    descripción, lienzo y recomendaciones. Ningún campo numérico: esos ya
    llegaron resueltos en ResultadoCalculo y este esquema no los repite,
    para que el agente no pueda contradecirlos (ASR-01)."""

    perfil_cultura_descripcion: str
    dimensiones_observaciones: dict[str, str]
    lienzo_negocio: dict[str, str]
    sintesis: str
    recomendaciones: list[RecomendacionAgente]
