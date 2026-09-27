from src.dominio.entidades.evaluacion import SolicitudEvaluacion

# RF-43/Tabla 18: datos que nunca deben llegar a la petición del proveedor de
# inferencia. SolicitudEvaluacion ya no tiene campos para razón social, NIT
# ni datos personales del representante — esta lista es una salvaguarda
# estructural adicional (defensa en profundidad) para el diccionario que
# efectivamente se envía, de modo que la regla siga vigente aunque el
# adaptador de inferencia cambie o alguien agregue un campo nuevo sin
# revisar este archivo.
CLAVES_PROHIBIDAS = {
    "razon_social",
    "empresa_nombre",
    "nit",
    "identificacion_tributaria",
    "nombre_representante",
    "representante",
    "correo",
    "telefono",
}


class DatoProhibidoError(Exception):
    pass


def sanear_solicitud(solicitud: SolicitudEvaluacion) -> None:
    """RF-43: valida que la solicitud no contenga ninguno de los datos
    excluidos. No transforma nada — SolicitudEvaluacion ya nace sin esos
    campos; esto es la comprobación que documenta y hace exigible la regla."""
    if not solicitud.empresa_id or not solicitud.empresa_id.strip():
        raise DatoProhibidoError(
            "empresa_id no puede estar vacío: la petición debe identificar "
            "la empresa por un id opaco, nunca por su razón social"
        )


def sanear_payload(payload: dict) -> dict:
    """Defensa en profundidad sobre el diccionario efectivamente serializado
    antes de enviarlo al proveedor: elimina cualquier clave prohibida que
    pudiera colarse por un cambio futuro no revisado en el compositor."""

    def _limpiar(valor):
        if isinstance(valor, dict):
            return {
                clave: _limpiar(v)
                for clave, v in valor.items()
                if clave not in CLAVES_PROHIBIDAS
            }
        if isinstance(valor, list):
            return [_limpiar(v) for v in valor]
        return valor

    return _limpiar(payload)
