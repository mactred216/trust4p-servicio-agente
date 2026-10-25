import os

from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from src.aplicacion.casos_uso.consultar_ejecuciones_agente import \
    ConsultarEjecucionesAgente
from src.aplicacion.casos_uso.evaluar_diagnostico import (
    ESPERA_REINTENTO_SEGUNDOS, EvaluarDiagnostico)
from src.aplicacion.casos_uso.gestionar_base_conocimiento import (
    ActualizarDocumento, CargarDocumento, DesactivarDocumento,
    ListarDocumentos, ReactivarDocumento)
from src.dominio.puertos.cliente_embeddings import ClienteEmbeddings
from src.dominio.puertos.cliente_inferencia import ClienteInferencia
from src.dominio.puertos.extractor_texto import ExtractorTexto
from src.infraestructura.clientes.cliente_embeddings_vertex_ai import \
    ClienteEmbeddingsVertexAI
from src.infraestructura.clientes.cliente_inferencia_vertex import \
    ClienteInferenciaVertex
from src.infraestructura.clientes.extractor_texto_pdf import ExtractorTextoPDF
from src.infraestructura.persistencia.conexion import obtener_base_datos
from src.infraestructura.persistencia.repositorio_mongo_documento_conocimiento import \
    RepositorioMongoDocumentoConocimiento
from src.infraestructura.persistencia.repositorio_mongo_ejecucion_agente import \
    RepositorioMongoEjecucionAgente
from src.infraestructura.persistencia.repositorio_mongo_fragmento_conocimiento import \
    RepositorioMongoFragmentoConocimiento
from src.infraestructura.persistencia.repositorio_mongo_sesion import \
    RepositorioMongoSesion


def obtener_repositorio_sesion(
    db: AsyncIOMotorDatabase = Depends(obtener_base_datos),
) -> RepositorioMongoSesion:
    return RepositorioMongoSesion(db)


def obtener_repositorio_documento_conocimiento(
    db: AsyncIOMotorDatabase = Depends(obtener_base_datos),
) -> RepositorioMongoDocumentoConocimiento:
    return RepositorioMongoDocumentoConocimiento(db)


def obtener_repositorio_fragmento_conocimiento(
    db: AsyncIOMotorDatabase = Depends(obtener_base_datos),
) -> RepositorioMongoFragmentoConocimiento:
    return RepositorioMongoFragmentoConocimiento(db)


def obtener_extractor_texto() -> ExtractorTexto:
    return ExtractorTextoPDF()


def obtener_cliente_embeddings() -> ClienteEmbeddings:
    return ClienteEmbeddingsVertexAI()


def obtener_caso_uso_cargar_documento(
    repo_documento: RepositorioMongoDocumentoConocimiento = Depends(
        obtener_repositorio_documento_conocimiento
    ),
    repo_fragmento: RepositorioMongoFragmentoConocimiento = Depends(
        obtener_repositorio_fragmento_conocimiento
    ),
    extractor: ExtractorTexto = Depends(obtener_extractor_texto),
    embeddings: ClienteEmbeddings = Depends(obtener_cliente_embeddings),
) -> CargarDocumento:
    return CargarDocumento(repo_documento, repo_fragmento, extractor, embeddings)


def obtener_caso_uso_actualizar_documento(
    repo_documento: RepositorioMongoDocumentoConocimiento = Depends(
        obtener_repositorio_documento_conocimiento
    ),
    repo_fragmento: RepositorioMongoFragmentoConocimiento = Depends(
        obtener_repositorio_fragmento_conocimiento
    ),
    extractor: ExtractorTexto = Depends(obtener_extractor_texto),
    embeddings: ClienteEmbeddings = Depends(obtener_cliente_embeddings),
) -> ActualizarDocumento:
    return ActualizarDocumento(repo_documento, repo_fragmento, extractor, embeddings)


def obtener_caso_uso_desactivar_documento(
    repo_documento: RepositorioMongoDocumentoConocimiento = Depends(
        obtener_repositorio_documento_conocimiento
    ),
    repo_fragmento: RepositorioMongoFragmentoConocimiento = Depends(
        obtener_repositorio_fragmento_conocimiento
    ),
) -> DesactivarDocumento:
    return DesactivarDocumento(repo_documento, repo_fragmento)


def obtener_caso_uso_reactivar_documento(
    repo_documento: RepositorioMongoDocumentoConocimiento = Depends(
        obtener_repositorio_documento_conocimiento
    ),
    repo_fragmento: RepositorioMongoFragmentoConocimiento = Depends(
        obtener_repositorio_fragmento_conocimiento
    ),
) -> ReactivarDocumento:
    return ReactivarDocumento(repo_documento, repo_fragmento)


def obtener_caso_uso_listar_documentos(
    repo_documento: RepositorioMongoDocumentoConocimiento = Depends(
        obtener_repositorio_documento_conocimiento
    ),
) -> ListarDocumentos:
    return ListarDocumentos(repo_documento)


def obtener_repositorio_ejecucion_agente(
    db: AsyncIOMotorDatabase = Depends(obtener_base_datos),
) -> RepositorioMongoEjecucionAgente:
    return RepositorioMongoEjecucionAgente(db)


def obtener_cliente_inferencia() -> ClienteInferencia:
    return ClienteInferenciaVertex()


def obtener_caso_uso_evaluar_diagnostico(
    repo_fragmento: RepositorioMongoFragmentoConocimiento = Depends(
        obtener_repositorio_fragmento_conocimiento
    ),
    embeddings: ClienteEmbeddings = Depends(obtener_cliente_embeddings),
    inferencia: ClienteInferencia = Depends(obtener_cliente_inferencia),
    repo_ejecucion: RepositorioMongoEjecucionAgente = Depends(
        obtener_repositorio_ejecucion_agente
    ),
) -> EvaluarDiagnostico:
    return EvaluarDiagnostico(
        repo_fragmento,
        embeddings,
        inferencia,
        repo_ejecucion,
        modelo=getattr(inferencia, "nombre_modelo", "gpt-oss-120b-maas"),
        espera_reintento_segundos=float(
            os.getenv("ESPERA_REINTENTO_SEGUNDOS", ESPERA_REINTENTO_SEGUNDOS)
        ),
    )


def obtener_caso_uso_consultar_ejecuciones_agente(
    repo_ejecucion: RepositorioMongoEjecucionAgente = Depends(
        obtener_repositorio_ejecucion_agente
    ),
) -> ConsultarEjecucionesAgente:
    return ConsultarEjecucionesAgente(repo_ejecucion)
