from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.api.dependencias import obtener_caso_uso_evaluar_diagnostico
from src.api.middleware.autenticacion_servicio import \
    requiere_servicio_autorizado
from src.aplicacion.casos_uso.evaluar_diagnostico import (EvaluacionFallida,
                                                          EvaluarDiagnostico)
from src.dominio.entidades.evaluacion import (DimensionCalculada,
                                              DimensionModelo, NivelModelo,
                                              PerfilCulturalCalculado,
                                              RespuestaDiagnostico,
                                              ResultadoCalculo,
                                              SolicitudEvaluacion)
from src.dominio.servicios.saneador import DatoProhibidoError

router = APIRouter(prefix="/evaluaciones", tags=["evaluaciones"])


class DimensionCalculadaRequest(BaseModel):
    codigo: str
    puntaje: Decimal


class PerfilCulturalCalculadoRequest(BaseModel):
    codigo: str


class ResultadoCalculoRequest(BaseModel):
    indice_global: Decimal
    nivel: int
    nivel_nombre: str
    nivel_descripcion: str
    dimensiones: list[DimensionCalculadaRequest]
    perfil_cultural: PerfilCulturalCalculadoRequest


class RespuestaDiagnosticoRequest(BaseModel):
    pregunta_codigo: str
    dimension_codigo: str
    enunciado: str
    tipo: str
    opciones_codigo: list[str] = []
    valor: Optional[Decimal] = None
    texto: Optional[str] = None


class DimensionModeloRequest(BaseModel):
    codigo: str
    nombre: str
    peso: Decimal
    orden: int


class NivelModeloRequest(BaseModel):
    nivel: int
    nombre: str
    descripcion: str
    umbral_min: Decimal
    umbral_max: Decimal


class SolicitudEvaluacionRequest(BaseModel):
    diagnostico_id: str
    empresa_id: str
    modelo_version: str
    resultado_calculo: ResultadoCalculoRequest
    respuestas: list[RespuestaDiagnosticoRequest]
    dimensiones_modelo: list[DimensionModeloRequest]
    niveles_modelo: list[NivelModeloRequest]


class RecomendacionResponse(BaseModel):
    dimension_codigo: str
    titulo: str
    contenido: str
    prioridad: int


class RespuestaAgenteResponse(BaseModel):
    perfil_cultura_descripcion: str
    dimensiones_observaciones: dict[str, str]
    lienzo_negocio: dict[str, str]
    sintesis: str
    recomendaciones: list[RecomendacionResponse]


def _a_solicitud(datos: SolicitudEvaluacionRequest) -> SolicitudEvaluacion:
    return SolicitudEvaluacion(
        diagnostico_id=datos.diagnostico_id,
        empresa_id=datos.empresa_id,
        modelo_version=datos.modelo_version,
        resultado_calculo=ResultadoCalculo(
            indice_global=datos.resultado_calculo.indice_global,
            nivel=datos.resultado_calculo.nivel,
            nivel_nombre=datos.resultado_calculo.nivel_nombre,
            nivel_descripcion=datos.resultado_calculo.nivel_descripcion,
            dimensiones=[
                DimensionCalculada(codigo=d.codigo, puntaje=d.puntaje)
                for d in datos.resultado_calculo.dimensiones
            ],
            perfil_cultural=PerfilCulturalCalculado(
                codigo=datos.resultado_calculo.perfil_cultural.codigo
            ),
        ),
        respuestas=[
            RespuestaDiagnostico(
                pregunta_codigo=r.pregunta_codigo,
                dimension_codigo=r.dimension_codigo,
                enunciado=r.enunciado,
                tipo=r.tipo,
                opciones_codigo=r.opciones_codigo,
                valor=r.valor,
                texto=r.texto,
            )
            for r in datos.respuestas
        ],
        dimensiones_modelo=[
            DimensionModelo(
                codigo=d.codigo, nombre=d.nombre, peso=d.peso, orden=d.orden
            )
            for d in datos.dimensiones_modelo
        ],
        niveles_modelo=[
            NivelModelo(
                nivel=n.nivel,
                nombre=n.nombre,
                descripcion=n.descripcion,
                umbral_min=n.umbral_min,
                umbral_max=n.umbral_max,
            )
            for n in datos.niveles_modelo
        ],
    )


@router.post(
    "",
    response_model=RespuestaAgenteResponse,
    summary="Evaluar un diagnóstico completado",
    description="RF-36 a RF-40. Invocado por trust4p-api-negocio, no por "
    "un navegador — requiere autenticación de servicio, no sesión de "
    "usuario.",
)
async def evaluar_diagnostico(
    datos: SolicitudEvaluacionRequest,
    caso_uso: EvaluarDiagnostico = Depends(obtener_caso_uso_evaluar_diagnostico),
    _=Depends(requiere_servicio_autorizado),
):
    solicitud = _a_solicitud(datos)
    try:
        resultado = await caso_uso.ejecutar(solicitud)
    except DatoProhibidoError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except EvaluacionFallida as e:
        raise HTTPException(status_code=502, detail=e.motivo)

    return RespuestaAgenteResponse(
        perfil_cultura_descripcion=resultado.perfil_cultura_descripcion,
        dimensiones_observaciones=resultado.dimensiones_observaciones,
        lienzo_negocio=resultado.lienzo_negocio,
        sintesis=resultado.sintesis,
        recomendaciones=[
            RecomendacionResponse(
                dimension_codigo=r.dimension_codigo,
                titulo=r.titulo,
                contenido=r.contenido,
                prioridad=r.prioridad,
            )
            for r in resultado.recomendaciones
        ],
    )
