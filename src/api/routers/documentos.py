from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from src.api.dependencias import (obtener_caso_uso_actualizar_documento,
                                  obtener_caso_uso_cargar_documento,
                                  obtener_caso_uso_desactivar_documento,
                                  obtener_caso_uso_listar_documentos,
                                  obtener_caso_uso_reactivar_documento)
from src.api.middleware.autorizacion import requiere_rol
from src.aplicacion.casos_uso.gestionar_base_conocimiento import (
    ActualizarDocumento, CargarDocumento, DesactivarDocumento,
    DocumentoIlegible, DocumentoNoEncontrado, ListarDocumentos,
    ReactivarDocumento)

router = APIRouter(prefix="/documentos", tags=["documentos"])

FORMATOS_PERMITIDOS = {"application/pdf"}


class DocumentoResponse(BaseModel):
    id: str
    titulo: str
    categoria: str
    version: str
    cargado_por: str
    fuente: Optional[str]
    activo: bool
    creado_en: datetime


def _a_response(documento) -> DocumentoResponse:
    return DocumentoResponse(
        id=documento.id,
        titulo=documento.titulo,
        categoria=documento.categoria,
        version=documento.version,
        cargado_por=documento.cargado_por,
        fuente=documento.fuente,
        activo=documento.activo,
        creado_en=documento.creado_en,
    )


async def _leer_pdf(archivo: UploadFile) -> bytes:
    if archivo.content_type not in FORMATOS_PERMITIDOS:
        raise HTTPException(
            status_code=400,
            detail="Formato no permitido: solo se aceptan documentos PDF",
        )
    return await archivo.read()


@router.post(
    "",
    response_model=DocumentoResponse,
    status_code=201,
    summary="Cargar un documento en la base de conocimiento",
    description="RF-41 paso 1. Exclusivo del administrador.",
)
async def cargar_documento(
    titulo: str = Form(...),
    categoria: str = Form(...),
    version: str = Form(...),
    fuente: Optional[str] = Form(None),
    archivo: UploadFile = File(...),
    caso_uso: CargarDocumento = Depends(obtener_caso_uso_cargar_documento),
    usuario_id: str = Depends(requiere_rol("administrador")),
):
    contenido = await _leer_pdf(archivo)
    try:
        documento = await caso_uso.ejecutar(
            cargado_por=usuario_id,
            titulo=titulo,
            categoria=categoria,
            version=version,
            contenido_archivo=contenido,
            fuente=fuente,
        )
    except DocumentoIlegible as e:
        raise HTTPException(status_code=422, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _a_response(documento)


@router.patch(
    "/{documento_id}",
    response_model=DocumentoResponse,
    summary="Actualizar un documento (nueva versión)",
    description="RF-41 paso 2. Crea una nueva versión y desactiva la "
    "anterior; no sobreescribe el documento existente.",
)
async def actualizar_documento(
    documento_id: str,
    version: str = Form(...),
    titulo: Optional[str] = Form(None),
    categoria: Optional[str] = Form(None),
    fuente: Optional[str] = Form(None),
    archivo: UploadFile = File(...),
    caso_uso: ActualizarDocumento = Depends(obtener_caso_uso_actualizar_documento),
    usuario_id: str = Depends(requiere_rol("administrador")),
):
    contenido = await _leer_pdf(archivo)
    try:
        documento = await caso_uso.ejecutar(
            cargado_por=usuario_id,
            documento_id=documento_id,
            version=version,
            contenido_archivo=contenido,
            titulo=titulo,
            categoria=categoria,
            fuente=fuente,
        )
    except DocumentoNoEncontrado:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    except DocumentoIlegible as e:
        raise HTTPException(status_code=422, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _a_response(documento)


@router.post(
    "/{documento_id}/desactivar",
    response_model=DocumentoResponse,
    summary="Desactivar un documento",
    description="RF-41 paso 3: sus fragmentos dejan de participar en la "
    "recuperación de contexto, sin eliminarse del histórico.",
)
async def desactivar_documento(
    documento_id: str,
    caso_uso: DesactivarDocumento = Depends(obtener_caso_uso_desactivar_documento),
    usuario_id: str = Depends(requiere_rol("administrador")),
):
    try:
        documento = await caso_uso.ejecutar(documento_id)
    except DocumentoNoEncontrado:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    except DocumentoIlegible as e:
        raise HTTPException(status_code=422, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _a_response(documento)


@router.post(
    "/{documento_id}/reactivar",
    response_model=DocumentoResponse,
    summary="Reactivar un documento",
)
async def reactivar_documento(
    documento_id: str,
    caso_uso: ReactivarDocumento = Depends(obtener_caso_uso_reactivar_documento),
    usuario_id: str = Depends(requiere_rol("administrador")),
):
    try:
        documento = await caso_uso.ejecutar(documento_id)
    except DocumentoNoEncontrado:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    except DocumentoIlegible as e:
        raise HTTPException(status_code=422, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _a_response(documento)


@router.get(
    "",
    response_model=list[DocumentoResponse],
    summary="Listar los documentos de la base de conocimiento",
)
async def listar_documentos(
    caso_uso: ListarDocumentos = Depends(obtener_caso_uso_listar_documentos),
    usuario_id: str = Depends(requiere_rol("administrador")),
):
    documentos = await caso_uso.ejecutar()
    return [_a_response(d) for d in documentos]
