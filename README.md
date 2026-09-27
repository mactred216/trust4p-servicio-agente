# Trust 4P — Servicio de evaluación asistida

Microservicio de inteligencia artificial del sistema Trust 4P (diagnóstico de madurez de innovación). Gestiona la base de conocimiento, compone el contexto para el modelo de lenguaje, invoca al proveedor de inferencia y valida su respuesta — conforme al [ADR-001](https://github.com/mactred216/trust4p-api-negocio/blob/main/docs/adr/0001-sesion-con-estado-no-jwt.md) y [ADR-005](https://github.com/mactred216/trust4p-api-negocio/blob/main/docs/adr/0005-separacion-calculo-deterministico-generacion-asistida.md) de [`trust4p-api-negocio`](https://github.com/mactred216/trust4p-api-negocio), que es la fuente de verdad del contexto completo del proyecto (documento de arquitectura, requisitos, diccionario de datos).

Este servicio **no calcula el índice de madurez** — lo recibe ya calculado desde `trust4p-api-negocio` y genera exclusivamente el perfil de cultura, el lienzo de negocio y las recomendaciones.

## Arquitectura

Hexagonal, igual que `trust4p-api-negocio`:

```
src/
├── dominio/          ← núcleo. Nunca importa de infraestructura/
│   ├── entidades/
│   ├── servicios/
│   └── puertos/         (interfaces ABC)
├── aplicacion/casos_uso/
├── infraestructura/
│   ├── persistencia/     (adaptadores MongoDB)
│   └── clientes/          (adaptador hacia el proveedor de inferencia)
└── api/
    ├── routers/
    └── middleware/
```

## Desarrollo local

```bash
pip install -r requirements.txt
cp .env.example .env   # completar MONGO_URI
uvicorn src.api.main:app --reload
pytest tests/unitarias -v
```
