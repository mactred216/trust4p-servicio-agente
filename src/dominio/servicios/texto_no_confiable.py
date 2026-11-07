"""C7: tratamiento del texto que no escribe el sistema y que llega al modelo
de lenguaje: el texto libre de las respuestas del diagnóstico y los
fragmentos recuperados de la base de conocimiento.

Dos riesgos distintos:
- Datos personales en el texto libre (RF-43, Tabla 36): la petición no lleva
  razón social, NIT ni datos del representante, pero una persona puede
  escribirlos dentro de una respuesta abierta. Se sustituyen por marcas
  genéricas antes de componer la petición.
- Instrucciones dirigidas al modelo (inyección de instrucciones): un texto
  que intenta cambiar las reglas, el formato o los resultados. Se detecta por
  patrones; la respuesta afectada se omite y el fragmento se excluye, y
  ambos quedan registrados en la auditoría de la ejecución.

Las dos detecciones son heurísticas y tienen falsos negativos conocidos
(documentados en tests/unitarias/dominio/test_texto_no_confiable.py). No
reemplazan la regla de la instrucción base que ordena tratar este texto como
datos, ni la validación del esquema de salida; son una capa más.
"""
import re
import unicodedata

MARCA_PERSONA = "[persona]"
MARCA_CORREO = "[correo]"
MARCA_TELEFONO = "[teléfono]"
MARCA_DOCUMENTO = "[documento]"
MARCA_ENLACE = "[enlace]"
MARCA_ORGANIZACION = "[organización]"

TEXTO_OMITIDO = "[respuesta omitida: contenía instrucciones dirigidas al asistente]"

_MAY = "A-ZÁÉÍÓÚÑÜ"
_MIN = "a-záéíóúñü"
_PALABRA_NOMBRE = rf"[{_MAY}][{_MIN}]+(?:-[{_MAY}][{_MIN}]+)?"
_PARTICULA = r"(?:de |del |de la |de los )?"
_APELLIDOS = rf"(?:\s+{_PARTICULA}{_PALABRA_NOMBRE}){{0,3}}"

# Nombres de pila frecuentes en Colombia. Los que también son palabras comunes
# (Rosa, Luz, Paz, Victoria...) solo cuentan si los sigue un apellido.
_NOMBRES = """
alejandro alejandra andres andrea angela antonio camilo camila carlos carolina catalina cesar claudia cristian
daniel daniela david diana diego eduardo elena fabian felipe fernanda fernando francisco gabriel gabriela german
gloria gustavo hector ivan jaime javier jairo jenny jessica jhon john jorge jose juan julian juliana julio karen
laura leonardo liliana lina lorena luis luisa manuel marcela marco maria mario marta martha mateo mauricio miguel
monica natalia nelson nicolas oscar pablo patricia paola pedro rafael ricardo roberto rodrigo ruben sandra santiago
sara sebastian sergio sofia sonia tatiana valentina valeria vanessa victor viviana wilson william yesica yolanda
adriana alba alberto alexander alexandra alfonso alvaro ana beatriz blanca brayan cristina edwin elkin erika
esteban gerardo gonzalo guillermo hernan hugo isabel jairo jhonatan johana kevin leidy lucia manuela marlon
milena nancy omar orlando ramiro raul rocio samuel sebastiana silvia stella susana teresa ximena yeison yuliana
""".split()
_NOMBRES_AMBIGUOS = {"rosa", "luz", "paz", "victoria", "pilar", "mercedes", "dolores", "esperanza", "consuelo",
                     "angeles", "amparo", "socorro", "gracia", "rocio", "alba", "blanca", "stella", "marco"}

_INDICIOS_PERSONA = (
    r"señor|señora|señorita|sr\.|sra\.|srta\.|don|doña|ing\.|ingeniero|ingeniera|dr\.|dra\.|doctor|doctora|"
    r"lic\.|licenciado|licenciada|profesor|profesora|compañero|compañera|colega|gerente|director|directora|"
    r"jefe|jefa|coordinador|coordinadora|analista|asistente|presidente|presidenta|fundador|fundadora|socio|socia"
)


# Palabras que tras un cargo no son un nombre («Gerente General»).
_CALIFICATIVOS_DE_CARGO = {
    "general", "comercial", "financiero", "financiera", "administrativo", "administrativa", "tecnico", "tecnica",
    "operativo", "operativa", "ejecutivo", "ejecutiva", "regional", "nacional", "de", "del", "innovacion",
    "proyectos", "operaciones", "talento", "mercadeo", "ventas", "calidad", "planeacion", "estrategia", "junior",
    "senior", "encargado", "encargada", "interino", "interina", "y",
}


def _sin_tildes(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn").lower()


_RE_CORREO = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", re.UNICODE)
_RE_CORREO_ESCRITO = re.compile(r"\b[\w.+-]+\s*(?:\(|\[)?\s*arroba\s*(?:\)|\])?\s*[\w-]+(?:\s*(?:punto|\.)\s*[a-z]{2,6})+\b", re.I)
_RE_ENLACE = re.compile(r"\bhttps?://\S+|\bwww\.\S+", re.I)
_RE_TELEFONO = re.compile(
    r"(?:(?:\+|00)\s?57[\s.-]?)?(?:\(?60[1-8]\)?[\s.-]?\d{3}[\s.-]?\d{4}|3\d{2}[\s.-]?\d{3}[\s.-]?\d{4})\b"
    r"|(?:(?:\+|00)\s?57[\s.-]?)\d{7,10}\b"
)
_RE_TELEFONO_CON_ROTULO = re.compile(
    r"\b(?P<rotulo>tel|cel|teléfono|telefono|celular|whatsapp|móvil|movil|fijo)(?P<sep>\.?\s*:?\s*)\d{3}[\s.-]?\d{4}\b", re.I
)
_RE_NIT = re.compile(r"\b(?:nit|n\.i\.t\.?)\s*(?:no\.?|n\.?°|número)?\s*[:#]?\s*\d[\d.\s]{6,13}\d(?:\s*-\s*\d)?", re.I)
_RE_NIT_FORMATO = re.compile(r"(?<![\d$.,])\b\d{3}\.\d{3}\.\d{3}\s*-\s*\d\b|\b\d{9}-\d\b")
_RE_CEDULA = re.compile(
    r"\b(?:c\.?\s?c\.?|cédula|cedula|documento|identificación|identificacion)\s*(?:de ciudadanía)?\s*"
    r"(?:no\.?|n\.?°|número)?\s*[:#]?\s*\d[\d.]{5,13}\d", re.I)
_RE_ORGANIZACION = re.compile(
    rf"\b(?:[{_MAY}0-9][\w&.'-]*\s+){{1,4}}(?:S\.?\s?A\.?\s?S\.?|S\.\s?A\.|SAS|Ltda\.?|LTDA\.?|E\.?S\.?P\.?|S\.?\s?en\s?C\.?)(?=\W|$)")
# Solo el indicio ignora mayúsculas; el nombre debe empezar con mayúscula.
_RE_INDICIO_NOMBRE = re.compile(
    rf"\b(?P<indicio>(?i:{_INDICIOS_PERSONA}))\s+(?P<nombre>{_PALABRA_NOMBRE}{_APELLIDOS})")
_VOCALES = {"a": "aá", "e": "eé", "i": "ií", "o": "oó", "u": "uúü", "n": "nñ"}


def _patron_nombre(nombre: str) -> str:
    letras = [f"[{_VOCALES.get(c, c)}]" for c in nombre]
    primera = _VOCALES.get(nombre[0], nombre[0])
    letras[0] = "[" + primera.upper() + "]"
    return "".join(letras)


_RE_NOMBRE_DE_PILA = re.compile(
    r"\b(?P<pila>" + "|".join(_patron_nombre(n) for n in sorted(_NOMBRES, key=len, reverse=True)) + r")\b"
    rf"(?P<apellidos>{_APELLIDOS})"
)
_RE_NOMBRE_AMBIGUO = re.compile(
    r"\b(?:" + "|".join(_patron_nombre(n) for n in sorted(_NOMBRES_AMBIGUOS, key=len, reverse=True)) + r")\b"
    rf"(?:\s+{_PARTICULA}{_PALABRA_NOMBRE}){{1,3}}"
)


def _reemplazar_nombres(texto: str, hallazgos: list[str]) -> str:
    def por_indicio(m: re.Match) -> str:
        nombre = m.group("nombre")
        if _sin_tildes(nombre.split()[0]) in _CALIFICATIVOS_DE_CARGO:
            return m.group(0)
        hallazgos.append("persona")
        return f"{m.group('indicio')} {MARCA_PERSONA}"

    texto = _RE_INDICIO_NOMBRE.sub(por_indicio, texto)

    def marca(_m: re.Match) -> str:
        hallazgos.append("persona")
        return MARCA_PERSONA

    texto = _RE_NOMBRE_DE_PILA.sub(marca, texto)
    return _RE_NOMBRE_AMBIGUO.sub(marca, texto)


def sanear_texto_libre(texto: str) -> tuple[str, list[str]]:
    """Sustituye los datos personales y de la organización reconocibles en un
    texto libre. Devuelve el texto saneado y la lista de tipos encontrados."""
    if not texto:
        return texto, []
    hallazgos: list[str] = []

    def sustituir(patron: re.Pattern, marca: str, tipo: str, t: str) -> str:
        def r(_m):
            hallazgos.append(tipo)
            return marca
        return patron.sub(r, t)

    t = sustituir(_RE_CORREO, MARCA_CORREO, "correo", texto)
    t = sustituir(_RE_CORREO_ESCRITO, MARCA_CORREO, "correo", t)
    t = sustituir(_RE_ENLACE, MARCA_ENLACE, "enlace", t)
    t = sustituir(_RE_NIT, MARCA_DOCUMENTO, "nit", t)
    t = sustituir(_RE_CEDULA, MARCA_DOCUMENTO, "cedula", t)
    t = sustituir(_RE_NIT_FORMATO, MARCA_DOCUMENTO, "nit", t)
    t = sustituir(_RE_TELEFONO, MARCA_TELEFONO, "telefono", t)

    def con_rotulo(m: re.Match) -> str:
        hallazgos.append("telefono")
        return m.group("rotulo") + m.group("sep") + MARCA_TELEFONO

    t = _RE_TELEFONO_CON_ROTULO.sub(con_rotulo, t)
    t = sustituir(_RE_ORGANIZACION, MARCA_ORGANIZACION, "organizacion", t)
    t = _reemplazar_nombres(t, hallazgos)
    return t, hallazgos


# ---------------- instrucciones dirigidas al modelo ----------------

_PATRONES_INSTRUCCION = [
    (r"\b(ignora|ignore|ignorar|ignoren|olvida|olvidar|olviden|omite|omitir|descarta|desobedece|forget|disregard)\b"
     r"[^.\n]{0,40}\b(instruccion\w*|indicacion\w*|reglas?|orden\w*|lo anterior|todo lo anterior|instructions?|rules|prompt|above|previous)\b",
     "anular_instrucciones"),
    (r"\b(no sigas|no obedezcas|no cumplas|do not follow)\b[^.\n]{0,30}\b(instruccion\w*|reglas?|instructions?|rules)\b",
     "anular_instrucciones"),
    (r"\b(a partir de ahora|desde ahora|from now on)\b[^.\n]{0,20}\b(eres|actua\w*|responde\w*|you are|act|respond)\b",
     "cambio_de_rol"),
    (r"\b(actua|actue|actuen|comportate)\s+como\s+(si fueras|si eras|un asistente|una ia|un modelo|otro asistente|chatgpt)\b"
     r"|\b(act as|you are now|eres ahora|ahora eres)\b", "cambio_de_rol"),
    (r"\b(prompt del sistema|system prompt|instruccion(es)? (base|del sistema)|mensaje del sistema|developer message)\b",
     "referencia_al_sistema"),
    (r"</?\s*(system|assistant|user|sistema|asistente)\s*>|\[/?inst\]|<\|im_(start|end)\|>|^\s*#{2,}\s*(system|sistema|instrucciones)",
     "marcas_de_rol"),
    (r"\b(asigna|asignale|asignen|pon|ponle|pongan|cambia|cambien|establece|fija|declara|devuelve|marca|califica)\b"
     r"[^.\n]{0,30}\b(indice|nivel|puntaje|calificacion|score)\b[^.\n]{0,25}"
     r"\b(maximo|maxima|optimizado|referente|100|10|cien|diez)\b", "alterar_resultado"),
    (r"\b(responde|devuelve|escribe|imprime|output|respond|reply)\b[^.\n]{0,15}\b(solo|solamente|unicamente|only)\b"
     r"[^.\n]{0,25}\b(con|el texto|la palabra|with|the word)\b", "imponer_salida"),
    (r"^\s*(configuracion del modelo|resultado calculado|respuestas del diagnostico|material de referencia recuperado|"
     r"formato de salida|reglas obligatorias|limites de comportamiento)\b", "suplantar_seccion"),
    (r"\b(revela|muestra|repite|imprime|reveal|print|repeat)\b[^.\n]{0,25}\b(instruccion\w*|prompt|reglas|instructions)\b",
     "extraer_instrucciones"),
]
_RE_INSTRUCCION = [(re.compile(p, re.I | re.M), tipo) for p, tipo in _PATRONES_INSTRUCCION]


def detectar_instrucciones(texto: str) -> list[str]:
    """Tipos de instrucción dirigida al modelo encontrados en el texto
    (lista vacía si no hay)."""
    if not texto:
        return []
    normal = _sin_tildes(texto)
    return sorted({tipo for patron, tipo in _RE_INSTRUCCION if patron.search(normal)})


def como_dato(texto: str) -> str:
    """Presenta un texto no confiable en una sola línea y entre comillas
    angulares, para que no pueda abrir secciones nuevas en la petición."""
    plano = " ".join((texto or "").split())
    return "«" + plano.replace("«", "\"").replace("»", "\"") + "»"
