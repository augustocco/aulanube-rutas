"""Construye la presentación (PowerPoint) y el guion del video (Word) de AulaNube Rutas.

Usa el tema de la presentación de la Unidad 1. Las cifras salen de docs/resultados/resultados.json
y las notas del orador de cada diapositiva son el mismo texto del guion.

    python scripts/construir_presentacion.py [enlace del video]
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import docx
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.dml import MSO_THEME_COLOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

RAIZ = Path(__file__).resolve().parent.parent
PLANTILLA = RAIZ.parent.parent / "Unidad 1" / "Presentacion-AulaNube.pptx"
SALIDA = RAIZ / "docs" / "presentacion" / "Presentacion-AulaNube-Rutas.pptx"
GUION = RAIZ / "docs" / "presentacion" / "Guion-video-AulaNube-Rutas.docx"
R = json.loads((RAIZ / "docs" / "resultados" / "resultados.json").read_text(encoding="utf-8"))
UML, RES, CAP = RAIZ / "docs" / "uml", RAIZ / "docs" / "resultados", RAIZ / "docs" / "capturas"
VIDEO = sys.argv[1] if len(sys.argv) > 1 else "youtu.be/(pendiente)"


def n(x, d=1):
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


A, F, U = R["E1"]["alfabetico"], R["E1"]["fecha"], R["E1"]["urgencia"]
E2, E3 = R["E2"], R["E3"]
MAX = str(max(int(k) for k in E2["v1"]))
PMAX = str(max(int(k) for k in E3["v1"]))
t = lambda v, c, tipo: E2[v][c]["por_tipo"][tipo]  # noqa: E731

prs = Presentation(str(PLANTILLA))
# Quitar las diapositivas de la Unidad 1 y conservar maestro, diseños y tema.
lista = prs.slides._sldIdLst
for sid in list(lista):
    prs.part.drop_rel(sid.rId)
    lista.remove(sid)
L = {l.name: l for l in prs.slide_layouts}
TX1, AC1, AC2, AC3, AC5, BG2 = (MSO_THEME_COLOR.TEXT_1, MSO_THEME_COLOR.ACCENT_1, MSO_THEME_COLOR.ACCENT_2,
                                MSO_THEME_COLOR.ACCENT_3, MSO_THEME_COLOR.ACCENT_5, MSO_THEME_COLOR.BACKGROUND_2)


def caja(s, x, y, w, h, texto, tam=14, color=TX1, negrita=False, cursiva=False, alin=None, ancla=MSO_ANCHOR.TOP,
         blanco=False):
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = ancla
    lineas = texto if isinstance(texto, list) else [texto]
    for i, linea in enumerate(lineas):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        if alin:
            p.alignment = alin
        r = p.add_run()
        r.text = linea
        r.font.size = Pt(tam)
        r.font.bold = negrita
        r.font.italic = cursiva
        if blanco:
            r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        else:
            r.font.color.theme_color = color
    return tb


def tarjeta(s, x, y, w, h, fondo=BG2):
    f = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    f.adjustments[0] = 0.04
    f.fill.solid()
    f.fill.fore_color.theme_color = fondo
    f.line.fill.background()
    f.shadow.inherit = False
    return f


def insignia(s, x, y, texto, color=AC1, d=0.42):
    c = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x), Inches(y), Inches(d), Inches(d))
    c.fill.solid(); c.fill.fore_color.theme_color = color
    c.line.fill.background(); c.shadow.inherit = False
    caja(s, x, y, d, d, texto, 13, negrita=True, alin=PP_ALIGN.CENTER, ancla=MSO_ANCHOR.MIDDLE, blanco=True)


def imagen(s, ruta, x, y, w=None, h=None, marco=True):
    """Si se dan ancho y alto, la imagen se ajusta dentro de esa caja sin deformarse y queda centrada."""
    if w and h:
        from PIL import Image
        ancho, alto = Image.open(ruta).size
        escala = min(w / ancho, h / alto)
        x, y = x + (w - ancho * escala) / 2, y + (h - alto * escala) / 2
        w, h = ancho * escala, alto * escala
    pic = s.shapes.add_picture(str(ruta), Inches(x), Inches(y), Inches(w) if w else None, Inches(h) if h else None)
    if marco:
        pic.line.color.rgb = RGBColor(0xD5, 0xEA, 0xE7)
        pic.line.width = Pt(1)
    return pic


def contenido(titulo, notas=""):
    s = prs.slides.add_slide(L["CONTENIDO"])
    s.placeholders[100].text = titulo
    if notas:
        s.notes_slide.notes_text_frame.text = notas
    return s


def puntos(s, x, y, w, items, paso=0.95, tam=14):
    for i, t in enumerate(items, 1):
        insignia(s, x, y + (i - 1) * paso, str(i))
        caja(s, x + 0.6, y + (i - 1) * paso - 0.03, w - 0.6, paso - 0.05, t, tam)


def datos(s, y, items, alto=2.4, colores=(AC1, AC2, AC3, AC1)):
    ancho = (9.0 - 0.2 * (len(items) - 1)) / len(items)
    for i, (cifra, desc) in enumerate(items):
        x = 0.5 + i * (ancho + 0.2)
        tarjeta(s, x, y, ancho, alto)
        caja(s, x + 0.22, y + 0.18, ancho - 0.4, 0.75, cifra, 32 if len(items) > 3 else 36, colores[i % len(colores)], True)
        caja(s, x + 0.22, y + 1.0, ancho - 0.4, alto - 1.1, desc, 13)



# ===================================================================== guion
# (tiempo, diapositiva, qué mostrar, qué decir). Se usa para las notas del orador y para el guion en Word.
BLOQUES = [
    ("0:00 – 0:40", "1 · Portada", "Voz sobre la portada.",
     "Hola, soy Augusto Cañola. Esta es la actividad 6 de la Unidad 3, «Navegando mareas». Cierro el caso de AulaNube, "
     "la plataforma de capacitación de las unidades 1 y 2, con un problema de navegación que cualquiera que haya usado "
     "una plataforma de cursos reconoce: entrar y no saber qué hacer primero."),
    ("0:40 – 1:50", "2 · Problema", "Señalar las tres cifras, de izquierda a derecha.",
     "Después del cargue de RRHH de la unidad anterior, el colaborador ya está matriculado. Entra y ve sus cursos en "
     "orden alfabético: primero dos electivos, luego la inducción, alturas y riesgo eléctrico. Nada le dice que su "
     "certificado de alturas vence pronto ni que el avanzado exige el básico. Medí lo que pasa si sigue esa lista: solo "
     f"el {n(A['a_tiempo_pct'], 0)} % de los cursos obligatorios termina a tiempo. Y por dentro, la plataforma hace "
     f"{n(t('v1', '1', 'ruta')['consultas_media'], 0)} consultas a la base solo para dibujar esa lista, como quien va a la "
     "bodega a traer un tornillo a la vez. El catálogo empeora a medida que bajas: la página 2.500 tarda "
     f"{n(E3['v1'][PMAX], 0)} milisegundos."),
    ("1:50 – 2:40", "3 · Sistemas reales", "Una tarjeta por familia.",
     "Para diseñar la solución miré cómo navegan otros sistemas. Una aplicación de mapas no te muestra las calles en "
     "orden alfabético: calcula la ruta más conveniente en un grafo con restricciones. Una tienda en línea con miles de "
     "productos no cuenta todo para mostrarte la página siguiente: continúa desde el último que viste, como un "
     "marcapáginas. Y un sistema de recomendación ordena según un puntaje tuyo. Aquí ese puntaje es la urgencia: qué "
     "vence primero y qué hay que hacer antes."),
    ("2:40 – 3:20", "4 · Escenarios", "Leer EN1 a EN4.",
     "Como en ATAM, convertí eso en cuatro escenarios medibles: que la ruta suba los cursos a tiempo, que «Continuar» "
     f"lleve en un clic a la lección pendiente, que con {MAX} usuarios simultáneos cada operación responda en menos de "
     "200 milisegundos y que el catálogo no se vuelva más lento al bajar. Trabajé individualmente, asumiendo por fases "
     "los roles de líder, investigador de patrones, diseñador UML y programador."),
    ("3:20 – 4:20", "5 · Componentes", "Recorrer el diagrama de arriba abajo.",
     "Este es el diagrama de componentes. El navegador guarda el historial; el servicio no guarda estado, así que se "
     "pueden poner varias instancias detrás de un balanceador. Dentro del servicio están las estrategias de ruta, el "
     "árbol del curso, el publicador de eventos, la caché y el repositorio. Abajo se ve la relación con las unidades "
     "anteriores: la malla de cargues de la Unidad 2 crea las matrículas que aquí se convierten en rutas."),
    ("4:20 – 5:30", "6 · Patrones", "Uno por tarjeta.",
     "Cada patrón resuelve un problema. Strategy: el orden de la ruta es intercambiable, así comparé tres criterios con "
     "los mismos datos. Composite: un curso tiene módulos y un módulo tiene lecciones, y todos responden «¿cuánto te "
     "falta?». Iterator: recorre ese árbol saltándose lo completado; «Continuar» no necesita saber cómo está armado el "
     "curso. Command: cada clic de navegación es un objeto, y el botón «Atrás» vive en el navegador. Observer: cuando "
     "completas una lección, se avisa a la caché para que borre tu ruta vieja. Y Cache-Aside: la ruta se guarda la "
     "primera vez que se pide y se reutiliza."),
    ("5:30 – 6:20", "7 · Secuencia", "Seguir la secuencia del diagrama.",
     "Así se ve «Continuar». Si tu ruta está en caché, ni siquiera toca la base. Si no, la arma con dos consultas "
     "agrupadas, la ordena por urgencia y el iterador entrega tu siguiente lección. Abajo, al completar una lección, el "
     "observador invalida tu ruta, y en la iteración 3 el avance va a una cola que un hilo guarda en lotes."),
    ("6:20 – 7:10", "8 · Algoritmo", "Señalar el ejemplo de alturas.",
     "El corazón es la ruta por urgencia. Piensen en un GPS que sabe que no puedes tomar la autopista sin pasar antes "
     "por el retorno. El avanzado de alturas vence el día 8 y necesita el básico; el básico vence con la campaña, el "
     "día 20. Si solo miro fechas, el básico parece no tener prisa. La estrategia por urgencia le hereda al básico la "
     "fecha del avanzado, menos el tiempo de estudio del avanzado. Así el básico pasa adelante y los dos quedan a tiempo."),
    ("7:10 – 9:40", "9 · Demostración", "Pantalla: https://rutas-v1.149-130-191-139.sslip.io y https://rutas.149-130-191-139.sslip.io, colaboradora Luisa Rodríguez Jaimes.",
     "Ahora el prototipo, desplegado en Oracle Cloud en el mismo clúster de la Unidad 1. A la izquierda, la versión 1: la misma operaria ve primero dos electivos y su alturas avanzado "
     "sale «tarde»; abajo se ve que la página costó 92 consultas. A la derecha, la versión 3: inducción, alturas básico "
     "y alturas avanzado, los cuatro obligatorios a tiempo, y la ruta salió de la caché sin tocar la base. Doy clic en "
     "«Continuar» y me lleva directo a la lección 3.1 de la inducción. Marco como completada y sigo: pasa a la 3.2. "
     "Vuelvo a «Mi ruta» y los minutos pendientes ya bajaron. Uso «Atrás», que es el historial de comandos. Por último, "
     "en el catálogo doy «Cargar 20 más» varias veces y cada página tarda lo mismo."),
    ("9:40 – 10:30", "10 · Ruta", "Señalar la barra gris y la verde; luego la gráfica derecha.",
     f"Con los 2.000 colaboradores de prueba, la ruta por urgencia subió los cursos obligatorios a tiempo de "
     f"{n(A['a_tiempo_pct'], 0)} % a {n(U['a_tiempo_pct'], 0)} %, y «Continuar» llevó a un curso obligatorio en casi el "
     "cien por ciento de los casos. La gráfica derecha muestra por qué no basta con «lo que vence primero»: en los "
     f"reentrenamientos con un curso previo pendiente, esa estrategia llega a {n(F['vencimientos_con_prerrequisito_a_tiempo_pct'], 0)} % "
     f"y la urgencia a {n(U['vencimientos_con_prerrequisito_a_tiempo_pct'], 0)} %."),
    ("10:30 – 11:40", "11 · Carga", "Izquierda: línea verde arriba. Derecha: la verde abajo.",
     f"La prueba de carga simula hasta {MAX} personas usando la plataforma a la vez. La iteración 2 aceleró las "
     f"lecturas: de {n(t('v1', '1', 'ruta')['consultas_media'], 0)} consultas a {n(t('v2', '1', 'ruta')['consultas_media'], 0)}. Pero, para mi sorpresa, con mucha gente no mejoró. El cuello de botella se había "
     "movido a la escritura: la base admite un solo escritor, y cada «Completar» esperaba su turno para escribir en "
     "disco, como una fila de una sola caja. En la iteración 3, el cajero anota en una libreta y pasa todo al sistema "
     f"cada 100 milisegundos. Resultado con {MAX} usuarios: de {n(E2['v1'][MAX]['rps'], 0)} a "
     f"{n(E2['v3'][MAX]['rps'], 0)} solicitudes por segundo, y el peor caso bajó de {n(E2['v1'][MAX]['p99_ms'] / 1000, 0)} "
     "segundos a una décima de segundo."),
    ("11:40 – 12:20", "12 · El cuello se mueve", "Recorrer las tres tarjetas.",
     "Esta es la lección más importante de la unidad: el cuello de botella se mueve. Primero eran las lecturas, luego "
     "la escritura y ahora es la CPU de un solo proceso; por eso, en la iteración 3, el rendimiento baja un poco al "
     "subir los usuarios. Como el servicio no tiene estado, el siguiente paso es poner varias instancias con una caché "
     "compartida. Cada mejora tuvo su costo: la ruta en caché puede estar desactualizada unos minutos y, si el servidor "
     "se cae, se pueden perder hasta 100 milisegundos de avance."),
    ("12:20 – 13:00", "13 · Catálogo", "Señalar la línea naranja que sube y la verde plana.",
     "Por último, el catálogo. Con OFFSET, para mostrarte la página 2.500 la base cuenta y descarta 50.000 cursos, como "
     f"leer un libro desde la primera página cada vez: {n(E3['v1'][PMAX], 0)} milisegundos. Con la paginación por llave, "
     "es un marcapáginas: cualquier página cuesta lo mismo, menos de una décima de milisegundo."),
    ("13:00 – 13:45", "14 · Conclusiones", "Cierre.",
     "Me quedo con tres ideas. Navegar bien es un problema de arquitectura: un criterio de orden subió el cumplimiento "
     "más que cualquier ajuste de pantalla. Medir antes de optimizar me mostró que el cuello de botella se mueve. Y "
     "cada patrón y cada optimización se justificaron por un problema concreto y con un costo explícito. El código, "
     "los diagramas y el informe están en el repositorio. Gracias."),
]

# =================================================================== diapositivas
# 1 · Portada
s = prs.slides.add_slide(L["PORTADA"])
s.placeholders[100].text = "AulaNube Rutas"
s.placeholders[101].text = "Estrategias de navegación optimizadas para las rutas de formación"
caja(s, 0.6, 0.5, 8.8, 0.35, "Arquitectura de Software · Unidad 3 · Actividad 6 «Navegando mareas: Estrategias de navegación en la arquitectura de software»", 12, blanco=True)
caja(s, 0.6, 3.75, 8.8, 0.35, f"Video: {VIDEO}", 14, negrita=True, blanco=True)
_r = s.shapes[-1].text_frame.paragraphs[0].runs[0]
if VIDEO.startswith("http"):
    _r.hyperlink.address = VIDEO
    _h = _r._r.find(qn("a:rPr")).find(qn("a:hlinkClick"))
    _ext = _h.makeelement(qn("a:extLst"), {})
    _e = _ext.makeelement(qn("a:ext"), {"uri": "{A12FA001-AC4F-418D-AE19-62706E023703}"})
    _e.append(_e.makeelement("{http://schemas.microsoft.com/office/drawing/2018/hyperlinkcolor}hlinkClr", {"val": "tx"}))
    _ext.append(_e); _h.append(_ext)
_r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
caja(s, 0.6, 4.35, 8.8, 0.3, "Augusto César Cañola Ortiz · Docente: Ing. Leydi Johana Polo Amador", 13, blanco=True)
caja(s, 0.6, 4.7, 8.8, 0.3, "Tecnológica del Oriente · Noviembre de 2026", 12, blanco=True)

# 2 · Problema
s = contenido("Entrar y no saber qué hacer primero")
caja(s, 0.5, 1.1, 9.0, 0.35, "Después del cargue de RRHH (Unidad 2), el colaborador ve «Mis cursos» en orden alfabético.", 15, AC5)
datos(s, 1.7, [
    (f"{n(A['a_tiempo_pct'], 0)} %", "de los cursos obligatorios termina a tiempo siguiendo la lista actual"),
    (f"{n(t('v1', '1', 'ruta')['consultas_media'], 0)}", "consultas SQL para dibujar la ruta de una persona (patrón N+1)"),
    (f"{n(E3['v1'][PMAX], 0)} ms", f"para la página {n(int(PMAX), 0)} del catálogo con OFFSET; la primera, {n(E3['v1']['1'], 0)} ms"),
], 2.6, (AC3, AC2, AC2))
caja(s, 0.5, 4.5, 9.0, 0.45, "Dos problemas de arquitectura: orientar al colaborador y no degradarse al crecer.", 15, AC1, cursiva=True)

# 3 · Sistemas reales
s = contenido("Cómo navegan otros sistemas")
for i, (tit, desc, aqui) in enumerate([
        ("Mapas", "Ruta de menor costo en un grafo con restricciones", "Prerrequisitos = orden topológico"),
        ("Comercio electrónico", "Filtros y «cargar más» desde el último producto visto", "Paginación por llave"),
        ("Recomendación", "Orden según un puntaje propio del usuario", "Puntaje = urgencia")]):
    x = 0.5 + i * 3.05
    tarjeta(s, x, 1.2, 2.85, 3.1)
    caja(s, x + 0.2, 1.38, 2.5, 0.4, tit, 17, AC1, True)
    caja(s, x + 0.2, 1.9, 2.5, 1.2, desc, 14)
    caja(s, x + 0.2, 3.35, 2.5, 0.8, "En AulaNube: " + aqui, 13, AC2, True)
caja(s, 0.5, 4.5, 9.0, 0.45, "Tres estrategias comparadas: alfabética (actual), primero lo que vence y urgencia con prerrequisitos.", 14, AC5)

# 4 · Escenarios
s = contenido("Escenarios de calidad (ATAM)")
for i, (tit, desc) in enumerate([
        ("EN1 · Efectividad", "Más cursos obligatorios terminados a tiempo que con el orden actual"),
        ("EN2 · Eficiencia", "«Continuar» lleva en 1 clic a la siguiente lección pendiente"),
        ("EN3 · Desempeño", f"Con {MAX} usuarios, p95 < 200 ms y Apdex ≥ 0,94"),
        ("EN4 · Escalabilidad", "La página siguiente del catálogo cuesta lo mismo a cualquier profundidad")]):
    x, y = 0.5 + (i % 2) * 4.6, 1.2 + (i // 2) * 1.55
    tarjeta(s, x, y, 4.4, 1.35)
    insignia(s, x + 0.25, y + 0.25, f"0{i + 1}", d=0.55)
    caja(s, x + 1.0, y + 0.2, 3.25, 0.35, tit, 15, negrita=True)
    caja(s, x + 1.0, y + 0.58, 3.25, 0.7, desc, 13)
caja(s, 0.5, 4.4, 9.0, 0.5, "Trabajo individual: los roles de líder, investigador de patrones, diseñador UML y programador se asumieron por fases.", 13, AC5)

# 5 · Componentes
s = contenido("Arquitectura: un servicio sin estado")
imagen(s, UML / "componentes.png", 0.5, 1.1, h=4.0)
puntos(s, 5.35, 1.25, 4.15, ["El historial «Atrás» vive en el navegador (Command)",
                             "Ruta y árbol del curso en caché (Cache-Aside)",
                             "Completar avisa por eventos (Observer)",
                             "Iteración 3: cola y escritor por lotes"], 0.95, 13)

# 6 · Patrones
s = contenido("Patrones elegidos para navegar")
pats = [("Strategy", "Criterio de orden de la ruta intercambiable"), ("Composite", "Curso > Módulo > Lección, todos dicen cuánto falta"),
        ("Iterator", "Siguiente lección pendiente sin conocer el árbol"), ("Command", "Cada clic es un objeto; «Atrás» sin estado en el servidor"),
        ("Observer", "Completar invalida solo tu ruta en caché"), ("Cache-Aside", "Se carga a petición y se invalida al cambiar"),
        ("Cola", "Escribir el avance sin hacer esperar al usuario"), ("Repository", "Tres implementaciones, una por iteración")]
for i, (tit, desc) in enumerate(pats):
    x, y = 0.5 + (i % 4) * 2.3, 1.15 + (i // 4) * 1.85
    tarjeta(s, x, y, 2.15, 1.7)
    caja(s, x + 0.17, y + 0.15, 1.85, 0.4, tit, 15, AC1, True)
    caja(s, x + 0.17, y + 0.65, 1.85, 0.95, desc, 12)

# 7 · Secuencia
s = contenido("Secuencia: «Continuar» y «Completar»")
imagen(s, UML / "secuencia.png", 0.5, 1.1, w=9.0, h=4.0)

# 8 · Algoritmo
s = contenido("Ruta por urgencia: el GPS de la formación")
imagen(s, UML / "actividad.png", 0.5, 1.1, h=4.0)
tarjeta(s, 4.2, 1.2, 5.3, 3.6)
caja(s, 4.45, 1.35, 4.9, 0.4, "Ejemplo", 16, AC1, True)
caja(s, 4.45, 1.85, 4.9, 2.9, [
    "• Alturas avanzado vence el día 8 y requiere el básico.",
    "• El básico vence con la campaña, el día 20.",
    "• «Primero lo que vence» ve al básico sin prisa → el avanzado sale tarde.",
    "• Urgencia: el básico hereda la fecha del avanzado menos 4 días de estudio → fecha efectiva día 4 → va primero y ambos quedan a tiempo."], 13)

# 9 · Demostración
s = prs.slides.add_slide(L["SECCION"])
s.placeholders[100].text = "Demostración"
s.placeholders[101].text = "En Oracle Cloud: rutas-v1.149-130-191-139.sslip.io (iteración 1) · rutas.149-130-191-139.sslip.io (iteración 3)"
for i, tx in enumerate(["Misma colaboradora en v1 y v3: orden, «tarde» y consultas SQL",
                        "«Continuar» lleva directo a la lección pendiente",
                        "Completar y seguir; la ruta se actualiza (Observer)",
                        "«Atrás» con el historial de comandos y «Cargar más» en el catálogo"], 1):
    insignia(s, 0.6, 3.15 + (i - 1) * 0.48, str(i), AC2, d=0.32)
    caja(s, 1.1, 3.15 + (i - 1) * 0.48, 8.3, 0.4, tx, 15, blanco=True)

# 10 · Ruta
s = contenido("La ruta por urgencia cumple más")
imagen(s, RES / "fig-ruta.png", 0.5, 1.2, w=6.3, marco=False)
for i, (c, d_) in enumerate([(f"{n(U['a_tiempo_pct'], 0)} %", f"obligatorios a tiempo (antes {n(A['a_tiempo_pct'], 0)} %)"),
                             (f"{n(U['colaboradores_al_dia_pct'], 0)} %", f"colaboradores al día (antes {n(A['colaboradores_al_dia_pct'], 0)} %)"),
                             (f"{n(U['continuar_lleva_a_obligatorio_pct'], 1)} %", f"«Continuar» lleva a un obligatorio (antes {n(A['continuar_lleva_a_obligatorio_pct'], 1)} %)")]):
    y = 1.2 + i * 1.25
    tarjeta(s, 7.0, y, 2.5, 1.1)
    caja(s, 7.15, y + 0.08, 2.25, 0.5, c, 22, AC1, True)
    caja(s, 7.15, y + 0.58, 2.25, 0.5, d_, 11)

# 11 · Carga
s = contenido(f"Con {MAX} usuarios simultáneos")
imagen(s, RES / "fig-carga.png", 0.5, 1.15, w=6.3, marco=False)
for i, (c, d_) in enumerate([(f"{n(E2['v1'][MAX]['rps'], 0)} → {n(E2['v3'][MAX]['rps'], 0)}", "solicitudes por segundo"),
                             (f"{n(t('v1', MAX, 'completar')['p95_ms'] / 1000, 0)} s → {n(t('v3', MAX, 'completar')['p95_ms'], 0)} ms", "p95 de «Completar»"),
                             (f"{n(E2['v1'][MAX]['p99_ms'] / 1000, 0)} s → {n(E2['v3'][MAX]['p99_ms'] / 1000, 2)} s", "p99 de todas las solicitudes")]):
    y = 1.2 + i * 1.25
    tarjeta(s, 7.0, y, 2.5, 1.1)
    caja(s, 7.15, y + 0.08, 2.25, 0.5, c, 17, AC1, True)
    caja(s, 7.15, y + 0.6, 2.25, 0.45, d_, 11)

# 12 · El cuello se mueve
s = contenido("El cuello de botella se mueve")
for i, (it, hall, cambio, costo, color) in enumerate([
        ("Iteración 2", "Lecturas N+1 y orden alfabético", "Consultas agrupadas, índices, caché, ruta por urgencia", "La ruta en caché puede quedar desactualizada", AC2),
        ("Iteración 3", "Escritura en fila de una sola caja", "Cola y escritura por lotes cada 100 ms", "Si se cae se pierden ≤ 100 ms de avance", AC1),
        ("Siguiente", "CPU de un solo proceso", "Varias instancias sin estado + caché compartida", "Infraestructura adicional", AC5)]):
    x = 0.5 + i * 3.05
    tarjeta(s, x, 1.2, 2.85, 3.5)
    insignia(s, x + 0.2, 1.38, str(i + 2) if i < 2 else "→", color)
    caja(s, x + 0.75, 1.42, 2.0, 0.4, it, 16, color, True)
    caja(s, x + 0.2, 2.0, 2.5, 0.75, "Hallazgo: " + hall, 13, negrita=True)
    caja(s, x + 0.2, 2.8, 2.5, 0.95, "Cambio: " + cambio, 12)
    caja(s, x + 0.2, 3.8, 2.5, 0.8, "Costo: " + costo, 12, AC3)

# 13 · Catálogo
s = contenido("Catálogo: un marcapáginas en lugar de contar")
imagen(s, RES / "fig-catalogo.png", 0.5, 1.2, w=6.0, marco=False)
puntos(s, 6.8, 1.35, 2.7, [f"OFFSET: página {n(int(PMAX), 0)} en {n(E3['v1'][PMAX], 0)} ms",
                           f"Keyset + índice: {n(E3['v2'][PMAX], 2)} ms en cualquier página",
                           "Cursor opaco y seguro para URL"], 1.1, 13)

# 14 · Conclusiones
s = prs.slides.add_slide(L["SECCION"])
s.placeholders[100].text = "Conclusiones"
s.placeholders[101].text = "Navegar bien es una decisión de arquitectura."
for i, tx in enumerate([f"Un criterio de orden subió los obligatorios a tiempo de {n(A['a_tiempo_pct'], 0)} % a {n(U['a_tiempo_pct'], 0)} %",
                        "Medir antes de optimizar mostró que el cuello de botella se mueve",
                        "Cada patrón resolvió un problema; cada optimización, con su costo explícito",
                        "Mismo caso de las unidades 1 y 2: AulaNube, de la matrícula a la ruta"]):
    caja(s, 0.8, 3.0 + i * 0.4, 8.6, 0.4, "•  " + tx, 14, blanco=True)
caja(s, 0.8, 4.7, 8.6, 0.3, "Repositorio: github.com/augustocco/aulanube-rutas", 11, blanco=True)

# Notas del orador y número de diapositiva
assert len(BLOQUES) == len(prs.slides._sldIdLst)
for sl, (tiempo, dia, pantalla, texto) in zip(prs.slides, BLOQUES):
    sl.notes_slide.notes_text_frame.text = f"[{tiempo}] {pantalla}\n\n{texto}"
for sl in list(prs.slides)[1:]:
    for ph in sl.slide_layout.placeholders:
        if ph.placeholder_format.type == 13:
            sl.shapes._spTree.append(copy.deepcopy(ph._element))
SALIDA.parent.mkdir(parents=True, exist_ok=True)
prs.save(str(SALIDA))
print("Presentación:", SALIDA, len(prs.slides._sldIdLst), "diapositivas")

# ======================================================================= guion
g = docx.Document()
g.styles["Normal"].font.name = "Calibri"
g.styles["Normal"].font.size = Pt(11)
for sec in g.sections:
    sec.left_margin = sec.right_margin = Inches(0.8)
g.add_heading("Guion del video · AulaNube Rutas", 0)
g.add_paragraph("Arquitectura de Software · Unidad 3 · Actividad 6 «Navegando mareas». Duración objetivo: 13 min 45 s "
                "(máximo 15). Subir a YouTube como «No listado».")
prep = g.add_paragraph()
prep.add_run("Antes de grabar: ").bold = True
prep.add_run("abrir en dos pestañas https://rutas-v1.149-130-191-139.sslip.io (iteración 1) y "
             "https://rutas.149-130-191-139.sslip.io (iteración 3), desplegadas en Oracle Cloud, y elegir a Luisa "
             "Rodríguez Jaimes. Para empezar con datos limpios, reiniciar los despliegues (cada pod recrea su base). "
             "En PowerPoint, usar la vista del moderador para leer las notas.")
tabla = g.add_table(rows=1, cols=3)
tabla.style = "Light Grid Accent 1"
for c, h in zip(tabla.rows[0].cells, ("Tiempo", "Diapositiva y pantalla", "Qué decir")):
    c.text = h
for tiempo, dia, pantalla, texto in BLOQUES:
    c = tabla.add_row().cells
    c[0].text, c[1].text, c[2].text = tiempo, f"{dia}\n{pantalla}", texto
for fila in tabla.rows:
    for i, w in enumerate((0.95, 1.8, 4.15)):
        fila.cells[i].width = Inches(w)
        for p in fila.cells[i].paragraphs:
            for r in p.runs:
                r.font.size = Pt(10)
g.save(str(GUION))
print("Guion:", GUION)
