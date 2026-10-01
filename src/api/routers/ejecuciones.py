from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.api.dependencias import obtener_caso_uso_consultar_ejecuciones_agente
from src.api.middleware.autorizacion import requiere_rol
from src.aplicacion.casos_uso.consultar_ejecuciones_agente import \
    ConsultarEjecucionesAgente

router = APIRouter(prefix="/ejecuciones", tags=["ejecuciones"])


class EjecucionAgenteResponse(BaseModel):
    id: str
    diagnostico_id: str
    intento: int
    peticion: dict[str, Any]
    fragmentos_recuperados: list[str]
    modelo_lenguaje_id: str
    version_plantilla_instrucciones: str
    estado: str
    respuesta: Optional[dict[str, Any]]
    motivo_fallo: Optional[str]
    creado_en: datetime


def _a_response(ejecucion) -> EjecucionAgenteResponse:
    return EjecucionAgenteResponse(
        id=ejecucion.id,
        diagnostico_id=ejecucion.diagnostico_id,
        intento=ejecucion.intento,
        peticion=ejecucion.peticion,
        fragmentos_recuperados=ejecucion.fragmentos_recuperados,
        modelo_lenguaje_id=ejecucion.modelo_lenguaje_id,
        version_plantilla_instrucciones=ejecucion.version_plantilla_instrucciones,
        estado=ejecucion.estado,
        respuesta=ejecucion.respuesta,
        motivo_fallo=ejecucion.motivo_fallo,
        creado_en=ejecucion.creado_en,
    )


@router.get(
    "/{diagnostico_id}",
    response_model=list[EjecucionAgenteResponse],
    summary="Consultar la bitácora de evaluación de un diagnóstico",
    description="RF-42: petición y respuesta de cada intento, en formato de "
    "solo lectura. Exclusivo del administrador.",
)
async def listar_ejecuciones_de_diagnostico(
    diagnostico_id: str,
    caso_uso: ConsultarEjecucionesAgente = Depends(
        obtener_caso_uso_consultar_ejecuciones_agente
    ),
    usuario_id: str = Depends(requiere_rol("administrador")),
):
    ejecuciones = await caso_uso.ejecutar(diagnostico_id)
    return [_a_response(e) for e in ejecuciones]
