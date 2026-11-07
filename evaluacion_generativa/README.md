# Evaluación del componente generativo (C9)

Este paquete evalúa lo que el agente redacta, más allá de que la respuesta
cumpla el esquema. Combina métricas automáticas y juicio experto. Las
métricas automáticas complementan el juicio experto; no lo sustituyen.

## Casos

`casos/C01.json` a `casos/C08.json` son diagnósticos **sintéticos y
anónimos** (empresa con identificador opaco, sin datos reales). Se generaron
con el código de la API de negocio (modelo sembrado 2026.1, motor de cálculo
y armado de la petición), así que cada `peticion` es exactamente lo que el
servicio recibe. `esperado` guarda lo que se puede verificar: índice, nivel,
puntajes, dimensión más baja, bloques del lienzo sin información y textos que
no deben aparecer en la salida.

| Caso | Qué pone a prueba |
|---|---|
| C01 | Madurez mínima (todo N1) |
| C02 | Madurez máxima (todo N4) |
| C03 | Respuestas mixtas, caso C del Anexo L (índice 59,375) |
| C04 | Perfil desigual: Propósito alto, Procesos en el mínimo |
| C05 | Texto libre con información de negocio (dos bloques del lienzo con sustento) |
| C06 | Texto libre que contradice las respuestas cerradas |
| C07 | Texto libre con instrucciones dirigidas al modelo |
| C08 | Texto libre con datos personales y de la organización |

**Separación.** Estos casos no se usaron para ajustar la plantilla de
instrucciones (versión 2.1). Si se usan para ajustarla, dejan de ser casos de
evaluación y hay que crear otros nuevos antes de volver a medir.

## Métricas automáticas (`metricas.py`)

| Métrica | Qué mide |
|---|---|
| Esquema | La respuesta pasa el validador del servicio |
| Fidelidad numérica | Cifras atribuidas al índice, un puntaje o un nivel que no coinciden con lo calculado |
| Anclaje de las observaciones | Proporción de dimensiones cuya observación cita al menos una respuesta de esa dimensión |
| Manejo de la falta de información | Proporción de bloques del lienzo sin sustento que el agente declara insuficientes; bloques que pudo haber inventado |
| Recomendaciones | Prioridades consecutivas, seis rótulos, cobertura de dimensiones, primera recomendación en la dimensión más baja |
| Seguridad | Ninguno de los textos prohibidos (instrucciones inyectadas, datos personales) aparece en la salida |
| Recuperación | Categorías de la base de conocimiento cubiertas y, con el juicio del experto, precisión de lo recuperado |

Límites conocidos: el anclaje y la insuficiencia se detectan por palabras,
así que pueden fallar ante paráfrasis; la fidelidad numérica solo revisa
cifras escritas cerca de «índice», «puntaje» o «nivel».

## Juicio experto

`plantilla_juicio_experto.csv` tiene una fila por caso y criterio, con
puntaje de 1 (inaceptable) a 4 (adecuado). Lo diligencia una persona de Trust
4P (idealmente dos, por separado). `juicio_experto.py` calcula la media y la
proporción de puntajes aceptables por criterio y, con dos evaluadores, el
acuerdo exacto, el acuerdo a un punto y la kappa ponderada.

## Cómo correrlo

```
# 1. Ejecutar los casos (servicio local con credenciales de Vertex, o el desplegado)
export AGENTE_API_KEY=...            # la clave entre servicios; no se guarda en archivos
python -m evaluacion_generativa.ejecutar --url https://<servicio-de-evaluacion> --salida resultados/AAAA-MM-DD

# 2. (Opcional) exportar los fragmentos recuperados de cada caso
MONGO_URI=... python -m evaluacion_generativa.exportar_fragmentos resultados/AAAA-MM-DD
python -m evaluacion_generativa.ejecutar --respuestas resultados/AAAA-MM-DD --salida resultados/AAAA-MM-DD

# 3. Juicio experto
python -m evaluacion_generativa.juicio_experto juicio_diligenciado.csv
```

Cada ejecución queda registrada en `ejecuciones_agente` con un
`diagnostico_id` que empieza por `c9-`.
