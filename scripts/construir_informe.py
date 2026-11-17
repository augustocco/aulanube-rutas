"""Construye docs/informe/Informe-AulaNube-Rutas.docx sobre la plantilla APA de la Unidad 1.

Las cifras salen de docs/resultados/resultados.json: ningún número se escribe a mano.
Después se abre en Word (scripts/actualizar_word.py) para actualizar la tabla de contenido.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import docx
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt
from docx.text.paragraph import Paragraph

RAIZ = Path(__file__).resolve().parent.parent
PLANTILLA = RAIZ.parent.parent / "Unidad 1" / "Informe-AulaNube.docx"
SALIDA = RAIZ / "docs" / "informe" / "Informe-AulaNube-Rutas.docx"
R = json.loads((RAIZ / "docs" / "resultados" / "resultados.json").read_text(encoding="utf-8"))
UML = RAIZ / "docs" / "uml"
RES = RAIZ / "docs" / "resultados"
CAP = RAIZ / "docs" / "capturas"

VIDEO = sys.argv[1] if len(sys.argv) > 1 else "[pendiente: enlace del video en YouTube, no listado]"
REPO = "https://github.com/augustocco/aulanube-rutas"


# ----------------------------------------------------------------- cifras
def n(x, d=1):
    s = f"{x:,.{d}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


E1 = R["E1"]
A, F, U = E1["alfabetico"], E1["fecha"], E1["urgencia"]
E2 = R["E2"]
MAX = str(max(int(k) for k in E2["v1"]))           # mayor concurrencia medida
UNO = "1"
t = lambda v, c, tipo: E2[v][c]["por_tipo"][tipo]  # noqa: E731
E3 = R["E3"]
PAGS = sorted(int(k) for k in E3["v1"])
PMAX = str(PAGS[-1])
APDEX_T = R.get("apdex_t_s", 0.2)


# ----------------------------------------------------------- documento
doc = docx.Document(str(PLANTILLA))
cuerpo = doc.element.body
hijos = list(cuerpo)
# Se conservan la portada (0-13), el título «Resumen» (14), su párrafo (15) y «Tabla de contenido» (16).
for k in hijos[17:]:
    if not k.tag.endswith("sectPr"):
        cuerpo.remove(k)
P = [Paragraph(k, doc) for k in hijos[:17]]


def poner_texto(p: Paragraph, texto: str) -> None:
    runs = p.runs
    runs[0].text = texto
    for r in runs[1:]:
        r._r.getparent().remove(r._r)


TITULO = ("AulaNube Rutas: estrategias de navegación optimizadas para las rutas de formación "
          "de la plataforma de CapacitaPro S.A.S.")
poner_texto(P[4], TITULO)
poner_texto(P[11], "Noviembre de 2026")
poner_texto(P[13], f"Video de presentación: {VIDEO} · Repositorio: {REPO}")
poner_texto(P[15], (
    "Este informe cierra el caso de CapacitaPro S.A.S. de las unidades 1 y 2 con un problema de navegación: el "
    "colaborador entra a la plataforma, ve una lista alfabética de cursos y no sabe cuál hacer primero, mientras se "
    "acercan el cierre de la campaña y el vencimiento de su certificado; además, el catálogo y la lección siguiente "
    "tardan más a medida que la plataforma crece. Se diseñó AulaNube Rutas, que calcula una ruta de formación por "
    "urgencia respetando prerrequisitos y lleva al colaborador a su siguiente lección con un clic. Se modeló en UML "
    "(componentes, clases, secuencia y actividad) con los patrones Strategy, Composite, Iterator, Command, Observer y "
    "Cache-Aside, y se evaluó en tres iteraciones con escenarios de calidad y pruebas de carga. Con la ruta por "
    f"urgencia, los cursos obligatorios a tiempo pasaron de {n(A['a_tiempo_pct'])} % a {n(U['a_tiempo_pct'])} %. Con "
    f"{MAX} usuarios concurrentes, el sistema pasó de {n(E2['v1'][MAX]['rps'], 0)} a "
    f"{n(E2['v3'][MAX]['rps'], 0)} solicitudes por segundo, y el percentil 99 bajó de "
    f"{n(E2['v1'][MAX]['p99_ms'] / 1000)} s a {n(E2['v3'][MAX]['p99_ms'] / 1000, 2)} s, después de que la "
    "evaluación mostrara que el cuello de botella se desplazaba de las lecturas a la escritura."))
P[15].add_run()
# La guía de la unidad no pide resumen: se quitan el título y el párrafo para cumplir el límite de páginas.
for k in (P[14]._p, P[15]._p):
    k.getparent().remove(k)

ancla = P[16]._p  # se inserta todo después del título de la tabla de contenido


def _insertar(elemento):
    global ancla
    ancla.addnext(elemento)
    ancla = elemento


def _runs(p: Paragraph, texto: str, tam: Pt | None = None) -> None:
    # Marcado mínimo: **negrita**, _cursiva_ y `código`.
    for parte in re.split(r"(\*\*[^*]+\*\*|_[^_]+_|`[^`]+`)", texto):
        if not parte:
            continue
        if parte.startswith("**"):
            r = p.add_run(parte[2:-2]); r.bold = True
        elif parte.startswith("_") and parte.endswith("_") and len(parte) > 2:
            r = p.add_run(parte[1:-1]); r.italic = True
        elif parte.startswith("`"):
            r = p.add_run(parte[1:-1]); r.font.name = "Consolas"; r.font.size = Pt(10.5)
        else:
            r = p.add_run(parte)
        if tam and not parte.startswith("`"):
            r.font.size = tam


def parrafo(texto: str, estilo: str = "parrafoApa") -> Paragraph:
    p = doc.add_paragraph(style=estilo)
    _runs(p, texto)
    _insertar(p._p)
    return p


def titulo(texto: str, nivel: int = 1, salto: bool = False) -> None:
    p = doc.add_paragraph(texto, style=f"Heading {nivel}")
    if salto:
        p.paragraph_format.page_break_before = True
    _insertar(p._p)


def vineta(texto: str) -> None:
    p = parrafo(texto)
    p.paragraph_format.first_line_indent = Inches(-0.25)
    p.paragraph_format.left_indent = Inches(0.75)
    p.runs[0].text = "•\t" + p.runs[0].text if p.runs else ""


def toc() -> None:
    p = doc.add_paragraph()
    r = p.add_run()
    for tipo, texto in (("begin", None), (None, ' TOC \\o "1-2" \\h \\z \\u '), ("separate", None),
                        (None, "Actualice la tabla de contenido."), ("end", None)):
        if tipo:
            fc = OxmlElement("w:fldChar"); fc.set(qn("w:fldCharType"), tipo); r._r.append(fc)
        elif "TOC" in texto:
            it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = texto; r._r.append(it)
        else:
            t = OxmlElement("w:t"); t.text = texto; r._r.append(t)
    _insertar(p._p)


def etiqueta(tipo: str, num: int, nombre: str) -> None:
    p = doc.add_paragraph(style="Normal")
    p.add_run(f"{tipo} {num}").bold = True
    p.paragraph_format.keep_with_next = True
    _insertar(p._p)
    p = doc.add_paragraph(style="Normal")
    p.add_run(nombre).italic = True
    p.paragraph_format.keep_with_next = True
    _insertar(p._p)


def nota(texto: str) -> None:
    p = doc.add_paragraph(style="Normal")
    r = p.add_run("Nota. "); r.italic = True; r.font.size = Pt(10)
    _runs(p, texto, Pt(10))
    _insertar(p._p)


CONT = {"Tabla": 0, "Figura": 0}


def tabla(nombre: str, encabezados: list[str], filas: list[list[str]], anchos: list[float], nota_txt: str) -> None:
    CONT["Tabla"] += 1
    etiqueta("Tabla", CONT["Tabla"], nombre)
    t = doc.add_table(rows=1, cols=len(encabezados))
    t.style = doc.styles["tablaApa"]
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    for i, (celda, texto) in enumerate(zip(t.rows[0].cells, encabezados)):
        celda.width = Inches(anchos[i])
        p = celda.paragraphs[0]; p.paragraph_format.keep_with_next = True
        p.paragraph_format.line_spacing = 1.5; p.paragraph_format.first_line_indent = 0
        r = p.add_run(texto); r.bold = True; r.font.size = Pt(10.5)
    tr = t.rows[0]._tr.get_or_add_trPr()
    for etq in ("w:cantSplit", "w:tblHeader"):
        tr.append(OxmlElement(etq))
    for k, fila in enumerate(filas):
        celdas = t.add_row().cells
        t.rows[-1]._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
        for i, (celda, texto) in enumerate(zip(celdas, fila)):
            celda.width = Inches(anchos[i])
            p = celda.paragraphs[0]
            p.paragraph_format.line_spacing = 1.5; p.paragraph_format.first_line_indent = 0
            _runs(p, texto, Pt(10.5))
            p.paragraph_format.keep_with_next = True  # tabla y nota en la misma página
            borde = OxmlElement("w:tcBorders"); b = OxmlElement("w:bottom")
            for k, v in (("w:val", "single"), ("w:sz", "4"), ("w:space", "0"), ("w:color", "BFBFBF")):
                b.set(qn(k), v)
            borde.append(b); celda._tc.get_or_add_tcPr().append(borde)
    _insertar(t._tbl)
    nota(nota_txt)


def figura(nombre: str, imagen: Path, ancho: float, nota_txt: str) -> None:
    CONT["Figura"] += 1
    etiqueta("Figura", CONT["Figura"], nombre)
    p = doc.add_paragraph(style="Normal")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = 0
    p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(str(imagen), width=Inches(ancho))
    _insertar(p._p)
    nota(nota_txt)


def referencia(texto: str) -> None:
    p = parrafo(texto)
    p.paragraph_format.first_line_indent = Inches(-0.5)
    p.paragraph_format.left_indent = Inches(0.5)



# ================================================================ contenido
toc()

titulo("Introducción", salto=True)
parrafo(
    "Evaluar una arquitectura es comprobar, con escenarios y mediciones, si cumple los atributos de calidad que se "
    "esperan de ella, y descubrir dónde están sus cuellos de botella antes de que los encuentren los usuarios "
    "(Bass et al., 2012). En las unidades anteriores se diseñaron AulaNube, la plataforma de capacitación de "
    "CapacitaPro S.A.S., y su malla de cargues masivos. Esta unidad se ocupa de lo que pasa después del cargue: el "
    "colaborador ya está matriculado y tiene que navegar la plataforma hasta cumplir su formación obligatoria.")
parrafo(
    f"El código, los diagramas y los resultados están en {REPO}.")

titulo("Plan del proyecto")
parrafo(
    "La guía propone equipos de tres o cuatro integrantes. Como en las unidades 1 y 2, el trabajo se desarrolló de "
    "forma individual y los cuatro roles se asumieron por fases, cada uno con un entregable verificable: líder de "
    "proyecto (alcance, informe y video), investigador de patrones (criterios y Tabla 2), diseñador UML (los cuatro "
    "diagramas) y programador del prototipo (servicio, repositorios, vista y 14 pruebas). Se usaron Python 3.13 con "
    "SQLite, PlantUML, unittest y Git.")

titulo("El problema de navegación")
titulo("Situación actual", 2)
parrafo(
    "Después del cargue de RRHH, un operario de la Constructora Los Andes entra a la plataforma y encuentra en "
    "«Mis cursos» una lista alfabética: dos electivos que alguien le asignó, la inducción SG-SST, riesgo eléctrico y "
    "trabajo en alturas. Nada le dice que la campaña cierra en tres semanas, que su certificado de alturas vence "
    "antes, ni que el nivel avanzado exige el básico. Empieza por el primero de la lista, que es un electivo. Para "
    "retomar donde iba tiene que abrir el curso y buscar a mano la lección pendiente.")
parrafo(
    "Al problema de orientación se suma uno de rendimiento. Para armar esa lista, la plataforma consulta lección por "
    f"lección el avance del colaborador: en la iteración 1 se midieron {n(t('v1', UNO, 'ruta')['consultas_media'], 0)} "
    f"consultas SQL para mostrar una sola ruta y {n(t('v1', UNO, 'continuar')['consultas_media'], 0)} para abrir la "
    "lección siguiente. El catálogo de electivos se pagina con OFFSET, de modo que cada página cuesta más que la "
    f"anterior: en un catálogo de 50.000 cursos, la página {PMAX} tardó {n(E3['v1'][PMAX])} ms frente a "
    f"{n(E3['v1']['1'])} ms la primera.")

titulo("Relevancia y criterios de diseño", 2)
parrafo(
    "El impacto es triple. Para el colaborador, más clics y cursos vencidos. Para la empresa cliente, incumplimiento "
    f"de la formación obligatoria: con el orden actual solo {n(A['a_tiempo_pct'])} % de los cursos obligatorios de "
    f"los 2.000 colaboradores de prueba terminaría a tiempo. Para CapacitaPro, un sistema que se degrada con cada "
    "cliente nuevo. Siguiendo el método ATAM, los criterios se expresaron como escenarios de calidad con un estímulo, "
    "una respuesta y una medida (EcuRed, s. f.; Bass et al., 2012), que se presentan en la Tabla 1.")
tabla("Escenarios de calidad que guían el diseño",
      ["ID", "Criterio", "Escenario y medida"],
      [["EN1", "Efectividad de la ruta", "Siguiendo la ruta propuesta, el porcentaje de cursos obligatorios terminados a tiempo sube frente al orden actual."],
       ["EN2", "Eficiencia de la navegación", "«Continuar» lleva en un clic a la siguiente lección pendiente de un curso obligatorio disponible."],
       ["EN3", "Desempeño", f"Con {MAX} usuarios concurrentes, el percentil 95 de cada operación es menor de {n(APDEX_T * 1000, 0)} ms (Apdex con T = {n(APDEX_T, 1)} s ≥ 0,94)."],
       ["EN4", "Escalabilidad del catálogo", "El costo de pedir la página siguiente no crece con la profundidad ni con el tamaño del catálogo."]],
      [0.55, 1.6, 4.35], "Elaboración propia con el formato de escenarios de Bass et al. (2012).")

titulo("Estrategias de navegación en sistemas reales", 2)
parrafo(
    "Se compararon tres familias de soluciones. Las aplicaciones de mapas modelan la red como un grafo con costos y "
    "restricciones y calculan la ruta de menor costo. Un plan de formación también es un grafo: los prerrequisitos "
    "imponen un orden topológico (Cormen et al., 2022). A eso se suma un criterio de planificación conocido, atender "
    "primero lo que vence antes (Liu y Layland, 1973). Los catálogos extensos del comercio electrónico combinan "
    "filtros con paginación por llave, que continúa desde el último registro visto en lugar de contar y descartar "
    "los anteriores (Winand, s. f.). Y los sistemas de recomendación ordenan según un puntaje propio del usuario; aquí "
    "ese puntaje es la urgencia.")

titulo("Diseño arquitectónico")
parrafo(
    "AulaNube Rutas es un servicio sin estado: el historial de navegación vive en el navegador y la ruta calculada en "
    "una caché, de modo que se pueden poner varias instancias detrás de un balanceador (Redwerk, 2025). La Figura 1 "
    "muestra sus componentes y su relación con las unidades 1 y 2: la malla de cargues crea las matrículas que esta "
    "unidad convierte en rutas.")
figura("Diagrama de componentes", UML / "componentes.png", 4.0,
       "Elaboración propia en PlantUML. La cola y el escritor de avance se agregaron en la iteración 3.")
figura("Diagrama de clases", UML / "clases.png", 6.5, "Elaboración propia en PlantUML.")
parrafo(
    "El diagrama de clases (Figura 2) muestra la lógica interna. El contenido es un árbol (Curso, Módulo y Lección) "
    "que un iterador recorre saltando lo completado. La ruta la calcula una estrategia intercambiable. El repositorio "
    "tiene tres implementaciones, una por iteración. La vista encapsula cada acción de navegación en un comando.")
titulo("Patrones de diseño seleccionados", 2)
tabla("Patrones y su pertinencia para la navegación",
      ["Patrón", "Problema que resuelve", "Dónde está"],
      [["Strategy", "Cambiar el criterio de orden de la ruta sin tocar el servicio; comparar tres estrategias en igualdad", "dominio/ruta.py"],
       ["Composite", "Tratar igual un curso, un módulo o una lección al sumar minutos pendientes", "dominio/contenido.py"],
       ["Iterator", "Encontrar la siguiente lección pendiente sin conocer la forma del árbol", "IteradorPendientes"],
       ["Command", "Cada acción de navegación es un objeto; el historial permite «Atrás» sin estado en el servidor", "vista/index.html"],
       ["Observer", "Completar una lección invalida la ruta en caché y deja bitácora, sin acoplar el registro de avance", "dominio/eventos.py"],
       ["Cache-Aside", "La ruta y el árbol del curso se cargan a petición y se invalidan al cambiar", "datos/repositorio.py"],
       ["Cola (iteración 3)", "Desacoplar la escritura del avance de la respuesta al usuario", "RepositorioAsincrono"]],
      [1.3, 3.6, 1.6], "Elaboración propia. Strategy, Composite, Iterator, Command y Observer, según Refactoring.Guru (s. f.); "
      "Cache-Aside carga a petición e invalida al cambiar (Microsoft, 2025).")
figura("Diagrama de secuencia de «Continuar» y «Completar»", UML / "secuencia.png", 6.0, "Elaboración propia en PlantUML.")
parrafo(
    "En la secuencia (Figura 3), si la ruta está en caché, «Continuar» no toca la base; si no, la arma con dos "
    "consultas agrupadas y el iterador entrega la lección pendiente. Al completar, el observador invalida solo la "
    "ruta de ese colaborador. La actividad de la Figura 4 detalla "
    "la estrategia por urgencia: cada prerrequisito hereda la fecha del curso que lo necesita, menos el tiempo de "
    "estudio de ese curso, y después se ordena topológicamente atendiendo primero la fecha efectiva más cercana.")
figura("Diagrama de actividad de la ruta por urgencia", UML / "actividad.png", 2.4, "Elaboración propia en PlantUML.")

titulo("Prototipo")
parrafo(
    "El prototipo es un servicio HTTP en Python 3.13, sin dependencias externas, sobre una base SQLite con datos "
    "ficticios: 5.000 cursos (12 obligatorios con prerrequisitos y el resto electivos), 44.853 lecciones y 2.000 "
    "colaboradores de las dos empresas del caso. La vista tiene tres pantallas: «Mi ruta», el lector de lecciones y "
    "el catálogo, y en cada respuesta muestra los milisegundos y las consultas SQL que costó; un parámetro elige "
    "la iteración (v1, v2 o v3). Las 14 pruebas automatizadas verifican el dominio "
    "y que la iteración 2 devuelva exactamente lo mismo que la 1, y la 3 lo mismo que la 2, con menos consultas.")
if (CAP / "ruta-v1-v3.png").exists():
    figura("La misma colaboradora con la ruta de la iteración 1 y de la iteración 3", CAP / "ruta-v1-v3.png", 6.2,
           "Capturas del prototipo. A la izquierda, orden alfabético; a la derecha, ruta por urgencia.")

titulo("Evaluación y optimización")
parrafo(
    "Se hicieron tres pruebas. E1 calcula la ruta de los 2.000 colaboradores con cada estrategia y estima, con sus "
    "minutos diarios de estudio, si cada curso obligatorio termina antes de su fecha límite. E2 es una prueba de "
    f"carga: 1, 10, 25 y {MAX} usuarios virtuales recorren durante 20 s el flujo completo (ruta, continuar, completar "
    f"y varias páginas del catálogo) contra el servidor real. Se mide el percentil 95 (p95) y el índice Apdex con "
    f"T = {n(APDEX_T, 1)} s, que da 1 punto a cada respuesta de hasta T segundos, medio punto a las de hasta 4T y 0 "
    "a las demás (New Relic, s. f.). E3 mide el costo de pedir la página N de un catálogo de 50.000 cursos. Con "
    f"{MAX} usuarios, la prueba E2 se repitió varias veces: el p99 varió entre 9,0 y 11,0 s en la iteración 1, entre "
    "7,3 y 11,6 s en la 2 y entre 0,10 y 0,12 s en la 3. Se informa la última corrida.")

titulo("Efectividad de la ruta", 2)
figura("Porcentaje de cursos obligatorios terminados a tiempo según la estrategia", RES / "fig-ruta.png", 5.6,
       f"Prueba E1 con 2.000 colaboradores y {U['cursos_obligatorios']:,} cursos obligatorios pendientes. "
       f"La gráfica derecha considera los {U['vencimientos_con_prerrequisito']} reentrenamientos que vencen y "
       "tienen un prerrequisito pendiente.".replace(",", "."))
parrafo(
    f"Con la ruta por urgencia, los cursos obligatorios a tiempo pasaron de {n(A['a_tiempo_pct'])} % a "
    f"{n(U['a_tiempo_pct'])} % y los colaboradores con toda su formación al día, de "
    f"{n(A['colaboradores_al_dia_pct'])} % a {n(U['colaboradores_al_dia_pct'])} %. «Continuar» llevó a un curso "
    f"obligatorio en {n(U['continuar_lleva_a_obligatorio_pct'])} % de los casos, frente a "
    f"{n(A['continuar_lleva_a_obligatorio_pct'])} % con el orden alfabético (EN1 y EN2). La diferencia entre "
    "«primero lo que vence» y la urgencia aparece donde importa: en los reentrenamientos de alturas que vencen y "
    f"exigen un curso previo pendiente, la primera llega a {n(F['vencimientos_con_prerrequisito_a_tiempo_pct'])} % y "
    f"la segunda a {n(U['vencimientos_con_prerrequisito_a_tiempo_pct'])} %, porque solo esta adelanta el prerrequisito.")

titulo("Desempeño bajo carga y cuello de botella", 2)
tabla(f"Resultados de la prueba de carga con {MAX} usuarios concurrentes",
      ["Indicador", "Iteración 1", "Iteración 2", "Iteración 3"],
      [["Solicitudes por segundo", *[n(E2[v][MAX]["rps"], 0) for v in ("v1", "v2", "v3")]],
       ["Consultas SQL para armar la ruta", *[n(t(v, MAX, "ruta")["consultas_media"], 0) for v in ("v1", "v2", "v3")]],
       ["p95 de «Mi ruta» (ms)", *[n(t(v, MAX, "ruta")["p95_ms"], 0) for v in ("v1", "v2", "v3")]],
       ["p95 de «Continuar» (ms)", *[n(t(v, MAX, "continuar")["p95_ms"], 0) for v in ("v1", "v2", "v3")]],
       ["p95 de «Completar» (ms)", *[n(t(v, MAX, "completar")["p95_ms"], 0) for v in ("v1", "v2", "v3")]],
       ["Apdex de «Completar»", *[n(t(v, MAX, "completar")["apdex"], 2) for v in ("v1", "v2", "v3")]],
       ["p99 de todas las solicitudes (ms)", *[n(E2[v][MAX]["p99_ms"], 0) for v in ("v1", "v2", "v3")]]],
      [2.6, 1.3, 1.3, 1.3], "Prueba E2, 20 s por nivel de concurrencia, el 17 de noviembre de 2026 en el equipo de desarrollo.")
figura("Rendimiento por iteración al aumentar los usuarios concurrentes", RES / "fig-carga.png", 5.8,
       "Prueba E2. El eje vertical derecho está en escala logarítmica.")
parrafo(
    "La iteración 2 atacó las lecturas: consultas agrupadas en lugar de N+1, índices que faltaban y caché a un lado "
    "para la ruta y el árbol del curso. Armar la ruta pasó de "
    f"{n(t('v1', UNO, 'ruta')['consultas_media'], 0)} a {n(t('v2', UNO, 'ruta')['consultas_media'], 0)} consultas y "
    f"«Continuar», de {n(t('v1', UNO, 'continuar')['p50_ms'])} a {n(t('v2', UNO, 'continuar')['p50_ms'])} ms en la "
    "mediana. Pero la prueba de carga mostró que el sistema no mejoraba con muchos usuarios: el cuello de botella se "
    "había desplazado a la escritura. SQLite admite un solo escritor y cada «Completar» esperaba su propia "
    f"confirmación en disco; con {MAX} usuarios, su p95 llegó a {n(t('v2', MAX, 'completar')['p95_ms'] / 1000)} s.")
parrafo(
    "La iteración 3 aplicó la recomendación de la unidad de delegar las tareas costosas a una cola (Redwerk, 2025). "
    "«Completar» deja el avance en una cola en memoria y responde; un hilo lo guarda cada 100 ms en una sola "
    "transacción, y las lecturas suman lo que todavía está en la cola para que el colaborador vea su avance de "
    f"inmediato. Con {MAX} usuarios, el rendimiento pasó de {n(E2['v2'][MAX]['rps'], 0)} a "
    f"{n(E2['v3'][MAX]['rps'], 0)} solicitudes por segundo y el p99 de {n(E2['v2'][MAX]['p99_ms'] / 1000)} s a "
    f"{n(E2['v3'][MAX]['p99_ms'] / 1000, 2)} s (EN3). La Figura 7 deja ver el siguiente límite: en la iteración 3 el "
    f"rendimiento baja de {n(E2['v3'][UNO]['rps'], 0)} a {n(E2['v3'][MAX]['rps'], 0)} solicitudes por segundo al subir "
    "los usuarios, porque ahora la restricción es la CPU de un solo proceso. Como el servicio no tiene estado, el "
    "siguiente paso es el escalado horizontal con una caché compartida.")

titulo("Escalabilidad del catálogo", 2)
figura("Costo de pedir la página N del catálogo", RES / "fig-catalogo.png", 4.8,
       "Prueba E3, mediana de 15 repeticiones por página en un catálogo de 50.000 cursos.")
parrafo(
    f"Con OFFSET, la base cuenta y descarta todas las filas anteriores: la página {PMAX} costó "
    f"{n(E3['v1'][PMAX])} ms. Con la paginación por llave y un índice sobre (título, id), cualquier página costó "
    f"alrededor de {n(E3['v2'][PMAX], 2)} ms, y ese costo no depende de la profundidad (EN4). La salvedad es que la paginación por llave no permite "
    "saltar a una página arbitraria, algo aceptable en un catálogo que se recorre con «Cargar más».")

titulo("Decisiones y compromisos", 2)
tabla("Optimizaciones por iteración y compromisos aceptados",
      ["Iteración", "Hallazgo", "Cambio", "Compromiso"],
      [["2", "Orden alfabético y N+1 en cada lectura", "Ruta por urgencia, consultas agrupadas, índices, caché y paginación por llave", "La ruta en caché puede durar hasta 5 min si el cambio no pasa por el servicio"],
       ["3", "La escritura serializada frena todo con carga", "Cola en memoria y escritura por lotes cada 100 ms", "Si el proceso se cae se pierden hasta 100 ms de avance"],
       ["Siguiente", "La CPU de un solo proceso", "Varias instancias detrás de un balanceador, caché compartida", "Infraestructura adicional"]],
      [0.9, 1.8, 2.2, 1.6], "Elaboración propia. Los compromisos son los que ATAM pide hacer explícitos (EcuRed, s. f.).")

titulo("Conclusiones")
parrafo(
    "El problema de navegación tenía dos caras y las dos eran de arquitectura. La de orientación se resolvió con un "
    "criterio de orden: tratar la formación como un grafo con fechas límite subió los cursos obligatorios a tiempo de "
    f"{n(A['a_tiempo_pct'])} % a {n(U['a_tiempo_pct'])} %, y un solo botón reemplazó la búsqueda manual de la "
    "lección pendiente.")
parrafo(
    "La lección principal de la evaluación es que el cuello de botella se desplaza. Al optimizar las lecturas, la "
    "escritura pasó a ser el límite. Al resolver la escritura con una cola, el límite pasó a ser la CPU de una sola "
    "instancia. Por eso la evaluación de desempeño es un proceso continuo y no un estado (Bass et al., 2012), y cada "
    "optimización debe hacer explícito su compromiso, que es lo que distingue una decisión de arquitectura de un "
    "ajuste de código.")

titulo("Referencias", salto=True)
for ref in (
    "Bass, L., Clements, P., & Kazman, R. (2012). _Software architecture in practice_ (3.ª ed.). Addison-Wesley.",
    "Cormen, T. H., Leiserson, C. E., Rivest, R. L., & Stein, C. (2022). _Introduction to algorithms_ (4.ª ed.). MIT Press.",
    "EcuRed. (s. f.). _Architecture Trade-off Analysis Method (ATAM)_. Recuperado el 17 de noviembre de 2026, de https://www.ecured.cu/Architecture_Trade-off_Analysis_Method_(ATAM)",
    "Liu, C. L., & Layland, J. W. (1973). Scheduling algorithms for multiprogramming in a hard-real-time environment. _Journal of the ACM, 20_(1), 46–61. https://doi.org/10.1145/321738.321743",
    "Microsoft. (2025, 11 de septiembre). _Patrón Cache-Aside_. Azure Architecture Center. https://learn.microsoft.com/es-es/azure/architecture/patterns/cache-aside",
    "New Relic. (s. f.). _Apdex: Medir la satisfacción del usuario_. Recuperado el 17 de noviembre de 2026, de https://docs.newrelic.com/es/docs/apm/new-relic-apm/apdex/apdex-measure-user-satisfaction/",
    "Redwerk. (2025, 18 de junio). _10 principios clave para construir una arquitectura de software escalable y un crecimiento a largo plazo_. https://redwerk.es/blog/arquitectura-de-software-escalable/",
    "Refactoring.Guru. (s. f.). _Catálogo de patrones de diseño_. Recuperado el 17 de noviembre de 2026, de https://refactoring.guru/es/design-patterns/catalog",
    "Winand, M. (s. f.). _Paginar a través del resultado_. Use The Index, Luke. Recuperado el 17 de noviembre de 2026, de https://use-the-index-luke.com/es/sql/resultados-parciales/paginar",
):
    referencia(ref)

SALIDA.parent.mkdir(parents=True, exist_ok=True)
doc.save(str(SALIDA))
print("Informe:", SALIDA, "· tablas:", CONT["Tabla"], "· figuras:", CONT["Figura"])
