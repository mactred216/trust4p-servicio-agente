import pytest

from src.infraestructura.persistencia.inicializacion import (INDICES,
                                                             crear_indices)


@pytest.mark.asyncio
async def test_crea_los_indices_del_servicio_y_es_idempotente(db):
    assert await crear_indices(db) == []
    assert await crear_indices(db) == []

    total = 0
    for coleccion in {c for c, _, _ in INDICES}:
        informacion = await db[coleccion].index_information()
        total += len(informacion) - 1  # sin _id_
    assert total == len(INDICES)
