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
VIDEO = sys.argv[1] if len(sys.argv) > 1 else ""


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
    ("", "3 · Sistemas reales", "Una tarjeta por familia: primero lo que hace ese sistema y luego, en naranja, cómo lo usé.",
     "Antes de diseñar miré cómo resuelven la navegación tres tipos de sistemas que todos usamos. Una aplicación de "
     "mapas no te muestra las calles en orden alfabético: te propone la mejor ruta y respeta las calles de un solo "
     "sentido. En AulaNube eso es respetar qué curso va antes de cuál. Una tienda en línea, cuando bajas por los "
     "productos, sigue desde el último que viste; eso lo usé en el catálogo. Y una plataforma de video te muestra "
     "primero lo que más te interesa; aquí, lo primero es lo más urgente."),
    ("", "4 · Escenarios", "Leer las cuatro tarjetas.",
     "Con eso definí cuatro metas medibles, que en ATAM se llaman escenarios de calidad: una situación y la respuesta "
     "que se espera, con un número para comprobarla. Uno: que más cursos obligatorios terminen a tiempo que con la "
     "lista de hoy. Dos: que «Continuar» lleve en un clic a la lección que falta. Tres: que con 50 personas a la vez, "
     "95 de cada 100 clics respondan en menos de dos décimas de segundo. Cuatro: que bajar en el catálogo no lo vuelva "
     "más lento. Trabajé de forma individual, asumiendo por fases los roles de líder, investigador de patrones, "
     "diseñador UML y programador."),
    ("", "5 · Arquitectura", "Recorrer las tres capas de arriba abajo.",
     "Así está armado, en tres capas. Arriba, el navegador del colaborador: las pantallas y el historial del botón "
     "«Atrás». En el medio, el servicio de rutas, que hace cuatro trabajos: ordena la ruta, recorre el curso, avisa "
     "cuando algo cambia y guarda en memoria lo que ya calculó. Un detalle importante: este servicio no guarda nada "
     "de cada usuario entre un clic y otro, como un cajero que no necesita conocerte para atenderte; por eso se pueden "
     "abrir varios iguales si llega más gente. Abajo, la base de datos del LMS, la misma de las unidades anteriores, "
     "donde la malla de cargues de la Unidad 2 deja las matrículas. Al lado, la cola de avance de la iteración 3."),
    ("", "6 · Diagrama de componentes", "Recorrer el diagrama de izquierda a derecha con el cursor.",
     "Este es el mismo dibujo en UML, el diagrama de componentes, y se lee de izquierda a derecha. A la izquierda, "
     "el colaborador y su navegador, con la vista y el navegador de comandos que guarda el historial. En el centro, "
     "el recuadro grande es el servicio de rutas: la API recibe el clic, el servicio de navegación reparte el trabajo "
     "entre las estrategias de ruta, el contenido del curso, el publicador de eventos y el repositorio, que usa la "
     "caché para lo que ya calculó y la cola con su escritor para guardar el avance. A la derecha, la base del LMS, "
     "que también alimentan el servicio de cursos de la Unidad 1 y la malla de cargues de la Unidad 2."),
    ("", "7 · Patrones", "Una tarjeta por patrón: nombre, comparación y ejemplo.",
     "Cada patrón resuelve un problema concreto y lo explico con algo cotidiano. Strategy es como elegir en el GPS "
     "«ruta más rápida» o «sin peajes»: cambia el criterio, no el mapa; así comparé el orden alfabético, por fecha y "
     "por urgencia. Composite es una caja que tiene cajas adentro: el curso tiene módulos y los módulos lecciones, y "
     "a cualquiera le puedo preguntar cuánto le falta. Iterator es el dedo que recorre el índice saltando lo ya "
     "leído: así «Continuar» encuentra tu lección pendiente. Command es como el historial del navegador: cada clic "
     "queda anotado y por eso funciona «Atrás». Observer es una suscripción: cuando completas una lección se avisa a "
     "quien le interese, y la memoria borra tu ruta vieja. Cache-Aside es apuntar en un papel lo que ya calculaste "
     "para no volver a calcularlo en cada clic."),
    ("", "8 · Secuencia", "Recorrer la fila de arriba y luego la de abajo.",
     "Esto es lo que pasa por dentro, paso a paso. Al dar clic en «Continuar», primero se pregunta si tu ruta ya "
     "está calculada en memoria; si no, se arma con solo dos consultas a la base y se ordena por urgencia. Luego se "
     "toma el primer curso que puedas empezar, el iterador busca la siguiente lección que te falta y se abre. Al "
     "marcar «Completada», el avance se anota en la cola, se avisa para borrar tu ruta vieja y se abre la lección "
     "siguiente. El diagrama de secuencia UML completo está en el informe, figura 3."),
    ("", "9 · Ruta por urgencia", "Comparar las dos filas del cronograma; señalar la línea punteada del día 8.",
     "Este es el corazón: cómo se ordena la ruta. Un ejemplo con tres cursos de 4 días cada uno. Alturas avanzado "
     "vence el día 8 y exige el básico; el básico y riesgo eléctrico vencen con la campaña, más adelante. Fila de "
     "arriba, «primero lo que vence»: el avanzado vence primero pero está bloqueado, así que la persona hace riesgo "
     "eléctrico, luego el básico, y el avanzado termina el día 12: tarde. Fila de abajo, urgencia: como el básico es "
     "requisito de algo que vence el día 8, hereda esa urgencia; tiene que terminar el día 4. Entonces va primero, el "
     "avanzado termina el día 8, a tiempo, y riesgo eléctrico también alcanza. Es el GPS que sabe que antes de la "
     "autopista hay que pasar por el retorno."),
    ("7:10 – 9:40", "9 · Demostración", "Pantalla: https://rutas-v1.149-130-191-139.sslip.io y https://rutas.149-130-191-139.sslip.io, colaboradora Luisa Rodríguez Jaimes.",
     "Ahora el prototipo, desplegado en Oracle Cloud en el mismo clúster de la Unidad 1. A la izquierda, la versión 1: la misma operaria ve primero dos electivos y su alturas avanzado "
     "sale «tarde»; abajo se ve que la página costó 92 consultas. A la derecha, la versión 3: inducción, alturas básico "
     "y alturas avanzado, los cuatro obligatorios a tiempo, y la ruta salió de la caché sin tocar la base. Doy clic en "
     "«Continuar» y me lleva directo a la lección 3.1 de la inducción. Marco como completada y sigo: pasa a la 3.2. "
     "Vuelvo a «Mi ruta» y los minutos pendientes ya bajaron. Uso «Atrás», que es el historial de comandos. Por último, "
     "en el catálogo doy «Cargar 20 más» varias veces y cada página tarda lo mismo."),
    ("9:40 – 10:30", "10 · Ruta", "Señalar las tres barras de arriba abajo; luego la tarjeta de Luisa y la de abajo.",
     "¿La ruta nueva ayuda a cumplir? Para responderlo simulé a los 2.000 colaboradores de prueba: cada uno estudia sus "
     "minutos diarios siguiendo el orden que le muestra la plataforma, y miré cuántos cursos obligatorios terminan "
     "antes de su fecha límite. Leámoslo como «de cada 100 cursos». Con el orden alfabético de hoy, "
     f"{round(A['a_tiempo_pct'])} de cada 100 terminan a tiempo; con la ruta por urgencia, {round(U['a_tiempo_pct'])}. "
     "El ejemplo es Luisa, la operaria de la demostración: con la lista de hoy empieza por dos electivos y su curso "
     "de alturas avanzado, que vence el 2 de diciembre, lo terminaría el 14, tarde. Con la ruta por urgencia hace "
     "primero la inducción y alturas básico, que es requisito, y termina alturas avanzado el 30 de noviembre, a "
     "tiempo. ¿Por qué no basta con ordenar por fecha? Abajo está la respuesta: en los reentrenamientos que dependen "
     f"de otro curso, ordenar por fecha logra {round(F['vencimientos_con_prerrequisito_a_tiempo_pct'])} de cada 100 y "
     f"la urgencia {round(U['vencimientos_con_prerrequisito_a_tiempo_pct'])}, porque solo la urgencia adelanta el "
     "curso que es requisito. Es como un GPS que sabe que antes de la autopista hay que pasar por el retorno."),
    ("10:30 – 11:40", "11 · Carga", "Señalar las tres barras; luego las dos tarjetas de la derecha.",
     f"Ahora, ¿aguanta mucha gente a la vez? Simulé {MAX} colaboradores durante 20 segundos haciendo lo de siempre: "
     "ver su ruta, continuar, marcar lecciones completadas y mirar el catálogo. Piénsenlo como un supermercado con "
     f"{MAX} clientes en caja. Las barras dicen cuántas solicitudes atiende el sistema por segundo: hoy "
     f"{round(E2['v1'][MAX]['rps'])}, con la iteración 2 {round(E2['v2'][MAX]['rps'])} y con la iteración 3 "
     f"{round(E2['v3'][MAX]['rps'])}, unas siete veces más. A la derecha está lo que siente el usuario. Al marcar una "
     f"lección como completada, hoy, 5 de cada 100 veces la persona espera {round(t('v1', MAX, 'completar')['p95_ms'] / 1000)} "
     f"segundos o más; con la iteración 3, nunca más de {n(t('v3', MAX, 'completar')['p95_ms'] / 1000, 2)} segundos. Y "
     f"la peor espera de todas, la de 1 de cada 100 clics, bajó de {round(E2['v1'][MAX]['p99_ms'] / 1000)} segundos a "
     f"{n(E2['v3'][MAX]['p99_ms'] / 1000, 1)}."),
    ("11:40 – 12:20", "12 · El cuello se mueve", "Recorrer las tres tarjetas de izquierda a derecha.",
     "¿Por qué hicieron falta tres iteraciones? Sigamos con el supermercado. En la iteración 1, el cajero busca el "
     f"precio de cada producto en una lista: armar la ruta de una persona costaba {round(t('v1', '1', 'ruta')['consultas_media'])} "
     "consultas a la base. En la iteración 2 le pusimos lector de código de barras: caché, índices y "
     f"{round(t('v2', '1', 'ruta')['consultas_media'])} consultas. Leer quedó rapidísimo, pero apareció otra fila: hay "
     "un solo datáfono para pagar. La base admite un solo escritor, y cada «Completar» esperaba su turno. Por eso la "
     "iteración 2 casi no mejoró con mucha gente. En la iteración 3, el cajero anota los pagos y los pasa todos juntos "
     "cada 100 milisegundos, y la fila desaparece. El siguiente tapón ya es que hay un solo cajero, la CPU de un solo "
     "servidor; la solución sería abrir más cajas, es decir, más instancias. Esa es la lección de la unidad: el cuello "
     "de botella se mueve, y cada mejora tiene su costo; por ejemplo, si el servidor se cae, se pueden perder hasta 100 "
     "milisegundos de avance."),
    ("12:20 – 13:00", "13 · Catálogo", "Señalar la barra naranja alta; luego las dos tarjetas de la derecha.",
     "Por último, ¿por qué el catálogo se pone lento al bajar? Imaginen un catálogo de 50.000 cursos, de 20 en 20. "
     "Pedir la página 2.500 es pedir los últimos 20 cursos. Hoy la base lo resuelve como quien busca la página 500 de "
     "un libro contando hoja por hoja desde el principio: cuenta y descarta los 49.980 cursos anteriores. Por eso la "
     f"página 1 tarda {n(E3['v1']['1'], 0)} milisegundos y la 2.500, {n(E3['v1'][PMAX], 0)}: trece veces más. La "
     "versión nueva usa un marcapáginas: recuerda el último curso que viste y continúa desde ahí, sin contar nada. "
     "Por eso cualquier página cuesta lo mismo, menos de una décima de milisegundo. Para quien busca un electivo, "
     "cada «Cargar 20 más» se siente igual de rápido al principio que al final."),
    ("13:00 – 13:45", "14 · Conclusiones", "Cierre.",
     "Me quedo con tres ideas. Navegar bien es un problema de arquitectura: un criterio de orden subió el cumplimiento "
     "más que cualquier ajuste de pantalla. Medir antes de optimizar me mostró que el cuello de botella se mueve. Y "
     "cada patrón y cada optimización se justificaron por un problema concreto y con un costo explícito. El código, "
     "los diagramas y el informe están en el repositorio. Gracias."),
]

# Duración de cada diapositiva en segundos; los tiempos del guion se calculan a partir de aquí.
DURACION = [40, 70, 45, 40, 50, 40, 70, 45, 50, 150, 50, 65, 45, 40, 45]
_reloj, _con_tiempo = 0, []
for _k, (_t, _dia, _pantalla, _texto) in enumerate(BLOQUES):
    _ini, _reloj = _reloj, _reloj + DURACION[_k]
    _con_tiempo.append((f"{_ini // 60}:{_ini % 60:02d} – {_reloj // 60}:{_reloj % 60:02d}",
                        f"{_k + 1} · {_dia.split(' · ', 1)[1]}", _pantalla, _texto))
BLOQUES = _con_tiempo
TOTAL = f"{_reloj // 60} min {_reloj % 60:02d} s"

# =================================================================== diapositivas
# 1 · Portada
s = prs.slides.add_slide(L["PORTADA"])
s.placeholders[100].text = "AulaNube Rutas"
s.placeholders[101].text = "Estrategias de navegación optimizadas para las rutas de formación"
caja(s, 0.6, 0.5, 8.8, 0.35, "Arquitectura de Software · Unidad 3 · Actividad 6 «Navegando mareas: Estrategias de navegación en la arquitectura de software»", 12, blanco=True)
if VIDEO:  # el enlace se agrega cuando exista el video: python scripts/construir_presentacion.py <enlace>
    caja(s, 0.6, 3.75, 8.8, 0.35, f"Video: {VIDEO}", 14, negrita=True, blanco=True)
    _r = s.shapes[-1].text_frame.paragraphs[0].runs[0]
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
for k, (tit, hace, aqui) in enumerate([
        ("Mapas", "Te proponen la mejor ruta y respetan las calles de un solo sentido", "Respetar qué curso va antes de cuál"),
        ("Tiendas en línea", "Al bajar, siguen desde el último producto que viste", "«Cargar 20 más» en el catálogo"),
        ("Plataformas de video", "Te muestran primero lo que más te interesa", "Primero lo más urgente")]):
    x = 0.5 + k * 3.05
    tarjeta(s, x, 1.2, 2.85, 3.1)
    caja(s, x + 0.2, 1.38, 2.5, 0.4, tit, 17, AC1, True)
    caja(s, x + 0.2, 1.9, 2.5, 1.2, hace, 14)
    caja(s, x + 0.2, 3.3, 2.5, 0.85, "En AulaNube: " + aqui, 13, AC2, True)
caja(s, 0.5, 4.5, 9.0, 0.45, "Se compararon tres órdenes para la ruta: alfabético (hoy), primero lo que vence y urgencia.", 14, AC5)

# 4 · Escenarios
s = contenido("Cuatro metas medibles (escenarios ATAM)")
for k, (tit, desc) in enumerate([
        ("Cumplir", "Más cursos obligatorios terminados a tiempo que con la lista de hoy"),
        ("Un clic", "«Continuar» lleva directo a la lección que falta"),
        ("Rapidez", f"Con {MAX} personas a la vez, 95 de cada 100 clics responden en menos de 0,2 s"),
        ("Catálogo", "Bajar en el catálogo no lo vuelve más lento")]):
    x, y = 0.5 + (k % 2) * 4.6, 1.2 + (k // 2) * 1.55
    tarjeta(s, x, y, 4.4, 1.35)
    insignia(s, x + 0.25, y + 0.25, f"0{k + 1}", d=0.55)
    caja(s, x + 1.0, y + 0.2, 3.25, 0.35, tit, 16, negrita=True)
    caja(s, x + 1.0, y + 0.6, 3.25, 0.7, desc, 13)
caja(s, 0.5, 4.4, 9.0, 0.5, "Trabajo individual: los roles de líder, investigador de patrones, diseñador UML y programador se asumieron por fases.", 13, AC5)

# 5 · Arquitectura en tres capas
s = contenido("¿Cómo está armado? Tres capas")
capas = [
    ("1 · Navegador del colaborador", ["Pantallas: Mi ruta, lección y catálogo", "Historial del botón «Atrás» (Command)"], AC1),
    ("2 · Servicio AulaNube Rutas · no guarda estado: se pueden abrir varios iguales",
     ["Ordena la ruta (Strategy)", "Recorre el curso (Composite + Iterator)", "Avisa cambios (Observer)", "Recuerda lo calculado (caché)"], AC2),
    ("3 · Base de datos del LMS (la misma de las unidades 1 y 2)", ["Cursos, lecciones, matrículas y avance"], AC5)]
for k, (tit, chips, color) in enumerate(capas):
    y = 1.1 + k * 1.3
    tarjeta(s, 0.5, y, 6.6, 1.1)
    caja(s, 0.7, y + 0.08, 6.3, 0.35, tit, 13, color, True)
    ancho = (6.2 - 0.12 * (len(chips) - 1)) / len(chips)
    for c, chip in enumerate(chips):
        cx = 0.7 + c * (ancho + 0.12)
        f = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(cx), Inches(y + 0.5), Inches(ancho), Inches(0.48))
        f.fill.solid(); f.fill.fore_color.rgb = RGBColor(0xFF, 0xFF, 0xFF); f.line.fill.background(); f.shadow.inherit = False
        caja(s, cx + 0.06, y + 0.5, ancho - 0.12, 0.48, chip, 11, alin=PP_ALIGN.CENTER, ancla=MSO_ANCHOR.MIDDLE)
    if k < 2:
        caja(s, 3.6, y + 1.08, 0.4, 0.22, "▼", 12, color, True, alin=PP_ALIGN.CENTER)
tarjeta(s, 7.3, 2.4, 2.2, 2.4)
caja(s, 7.45, 2.5, 1.95, 0.35, "Cola de avance", 14, AC1, True)
caja(s, 7.45, 2.9, 1.95, 1.8, "Iteración 3: al completar una lección se anota aquí y un hilo la guarda en la base cada 100 ms.", 11)
caja(s, 7.3, 1.15, 2.2, 1.1, "La malla de cargues (Unidad 2) crea las matrículas en la misma base.", 11, AC5, cursiva=True)

# 6 · Diagrama de componentes (UML)
s = contenido("Diagrama de componentes (UML)")
imagen(s, UML / "componentes-ancho.png", 0.5, 1.3, w=9.0, h=3.2)
for k, (tit, color) in enumerate([("1 · Navegador", AC1), ("2 · Servicio de rutas", AC2), ("3 · Base del LMS", AC5)]):
    caja(s, [0.6, 3.6, 8.2][k], 4.6, 2.2, 0.35, tit, 13, color, True)

# 7 · Patrones
s = contenido("Patrones elegidos para navegar")
pats = [("Strategy", "Como elegir en el GPS «más rápida» o «sin peajes»", "Alfabético, por fecha o por urgencia"),
        ("Composite", "Una caja con cajas adentro", "Curso > módulos > lecciones: ¿cuánto falta?"),
        ("Iterator", "El dedo que recorre el índice saltando lo leído", "«Continuar» halla tu lección pendiente"),
        ("Command", "El historial del navegador", "Cada clic queda anotado: botón «Atrás»"),
        ("Observer", "Una suscripción que avisa", "Al completar, se borra tu ruta vieja"),
        ("Cache-Aside", "Apuntar en un papel lo ya calculado", "La ruta no se recalcula en cada clic")]
for k, (tit, como, ejemplo) in enumerate(pats):
    x, y = 0.5 + (k % 3) * 3.05, 1.15 + (k // 3) * 1.9
    tarjeta(s, x, y, 2.85, 1.75)
    caja(s, x + 0.2, y + 0.12, 2.5, 0.4, tit, 16, AC1, True)
    caja(s, x + 0.2, y + 0.55, 2.5, 0.6, como, 13, negrita=True)
    caja(s, x + 0.2, y + 1.15, 2.5, 0.55, ejemplo, 12, AC5)

# 8 · Secuencia simplificada
s = contenido("¿Qué pasa por dentro al dar clic?")
filas = [("Al dar clic en «Continuar»", ["¿Tu ruta ya está calculada? Si no: 2 consultas y se ordena por urgencia",
                                           "Toma el primer curso que puedes empezar",
                                           "El iterador busca la siguiente lección que falta",
                                           "Se abre la lección"], AC1),
         ("Al marcar «Completada»", ["El avance se anota en la cola (sin esperar al disco)",
                                      "Se avisa: se borra tu ruta vieja de la memoria",
                                      "Se abre la lección siguiente"], AC2)]
for r, (tit, pasos, color) in enumerate(filas):
    y = 1.15 + r * 1.85
    caja(s, 0.5, y, 9.0, 0.35, tit, 15, color, True)
    ancho = (9.0 - 0.3 * (len(pasos) - 1)) / len(pasos)
    for k, paso in enumerate(pasos):
        x = 0.5 + k * (ancho + 0.3)
        tarjeta(s, x, y + 0.42, ancho, 1.2)
        insignia(s, x + 0.12, y + 0.52, str(k + 1), color, d=0.34)
        caja(s, x + 0.12, y + 0.92, ancho - 0.24, 0.68, paso, 11)
        if k < len(pasos) - 1:
            caja(s, x + ancho + 0.02, y + 0.85, 0.26, 0.3, "→", 16, color, True, alin=PP_ALIGN.CENTER)
caja(s, 0.5, 4.85, 9.0, 0.3, "Diagrama de secuencia UML completo: informe, figura 3.", 11, AC5, cursiva=True)

# 9 · Ruta por urgencia con un ejemplo
s = contenido("Ruta por urgencia: un ejemplo con 3 cursos")
caja(s, 0.5, 1.05, 9.0, 0.45, "Cada curso dura 4 días. Alturas avanzado vence el día 8 y exige el básico; los otros vencen después.", 13, AC5)
imagen(s, RES / "ppt-urgencia.png", 0.4, 1.5, w=6.3, h=2.6, marco=False)
tarjeta(s, 6.9, 1.6, 2.6, 2.45)
caja(s, 7.05, 1.7, 2.35, 0.35, "La regla", 15, AC1, True)
caja(s, 7.05, 2.1, 2.35, 1.9, "Si un curso es requisito de otro que vence pronto, hereda su urgencia: el básico debe terminar el día 8 − 4 = día 4.", 12)
caja(s, 0.5, 4.3, 9.0, 0.55, "Ordenar solo por fecha deja el básico para después y el avanzado sale tarde (✗). La urgencia lo adelanta y todo queda a tiempo (✓).", 13, AC1, True)
caja(s, 0.5, 4.88, 9.0, 0.3, "Diagrama de actividad UML del algoritmo: informe, figura 4.", 11, AC5, cursiva=True)

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
s = contenido("¿La ruta nueva ayuda a cumplir a tiempo?")
caja(s, 0.5, 1.05, 9.0, 0.5, "Simulación con 2.000 colaboradores: de cada 100 cursos obligatorios, ¿cuántos terminan antes de su fecha límite?", 14, AC5)
imagen(s, RES / "ppt-ruta.png", 0.4, 1.6, w=5.6, h=2.4, marco=False)
tarjeta(s, 6.2, 1.6, 3.3, 2.4)
caja(s, 6.4, 1.72, 2.95, 0.35, "Ejemplo: Luisa, operaria", 14, AC1, True)
caja(s, 6.4, 2.1, 2.95, 1.85, ["Hoy: empieza por 2 electivos. Alturas avanzado vence el 2 dic y lo termina el 14 dic → tarde.",
                               "Con urgencia: inducción → alturas básico → alturas avanzado, que termina el 30 nov → a tiempo."], 11)
tarjeta(s, 0.5, 4.15, 9.0, 0.75)
caja(s, 0.7, 4.22, 8.6, 0.65,
     f"Donde más se nota: reentrenamientos que dependen de otro curso. Alfabético {round(A['vencimientos_con_prerrequisito_a_tiempo_pct'])} · "
     f"por fecha {round(F['vencimientos_con_prerrequisito_a_tiempo_pct'])} · urgencia {round(U['vencimientos_con_prerrequisito_a_tiempo_pct'])} "
     "de cada 100, porque solo la urgencia adelanta el curso que es requisito.", 13, negrita=True, ancla=MSO_ANCHOR.MIDDLE)

# 11 · Carga
s = contenido(f"¿Aguanta {MAX} personas a la vez?")
caja(s, 0.5, 1.05, 9.0, 0.5, f"Prueba de carga: {MAX} colaboradores simulados durante 20 s viendo su ruta, continuando, completando lecciones y viendo el catálogo.", 13, AC5)
imagen(s, RES / "ppt-carga.png", 0.4, 1.6, w=5.6, h=3.2, marco=False)
for i, (antes, despues, desc) in enumerate([
        (f"{round(t('v1', MAX, 'completar')['p95_ms'] / 1000)} s", f"{n(t('v3', MAX, 'completar')['p95_ms'] / 1000, 2)} s",
         "Al marcar una lección completada, 5 de cada 100 veces se espera esto o más"),
        (f"{round(E2['v1'][MAX]['p99_ms'] / 1000)} s", f"{n(E2['v3'][MAX]['p99_ms'] / 1000, 1)} s",
         "La peor espera: la de 1 de cada 100 clics")]):
    y = 1.65 + i * 1.6
    tarjeta(s, 6.2, y, 3.3, 1.45)
    caja(s, 6.4, y + 0.1, 2.95, 0.55, f"{antes} → {despues}", 22, AC1, True)
    caja(s, 6.4, y + 0.7, 2.95, 0.7, desc, 11)
caja(s, 6.2, 4.85, 3.3, 0.3, "Hoy → iteración 3", 10, AC5, cursiva=True)

# 12 · El cuello se mueve
s = contenido("El cuello de botella se mueve")
caja(s, 0.5, 1.05, 9.0, 0.4, "Como en un supermercado: al quitar una fila, aparece la siguiente.", 15, AC5, cursiva=True)
etapas = [
    ("1", "Iteración 1 · hoy", "El cajero busca el precio de cada producto en una lista",
     f"{round(t('v1', '1', 'ruta')['consultas_media'])} consultas para armar una ruta", f"{round(E2['v1'][MAX]['rps'])} solicitudes/s", AC3),
    ("2", "Iteración 2", "Lector de código de barras… pero un solo datáfono para pagar",
     f"Leer: {round(t('v2', '1', 'ruta')['consultas_media'])} consultas. Escribir: un solo escritor, todos en fila", f"{round(E2['v2'][MAX]['rps'])} solicitudes/s", AC2),
    ("3", "Iteración 3", "Anota los pagos y los pasa juntos cada 100 ms",
     "El avance va a una cola y se guarda por lotes", f"{round(E2['v3'][MAX]['rps'])} solicitudes/s", AC1)]
for k, (num_, tit, analogia, tecnico, cifra, color) in enumerate(etapas):
    x = 0.5 + k * 3.05
    tarjeta(s, x, 1.6, 2.85, 2.75)
    insignia(s, x + 0.2, 1.75, num_, color)
    caja(s, x + 0.75, 1.8, 2.0, 0.35, tit, 14, color, True)
    caja(s, x + 0.2, 2.35, 2.5, 0.85, analogia, 13, negrita=True)
    caja(s, x + 0.2, 3.2, 2.5, 0.6, tecnico, 11, AC5)
    caja(s, x + 0.2, 3.85, 2.5, 0.4, cifra, 16, color, True)
caja(s, 0.5, 4.5, 9.0, 0.45, "Siguiente tapón: un solo cajero (la CPU de un servidor) → abrir más cajas (más instancias sin estado).", 13, AC1, True)

# 13 · Catálogo
s = contenido("¿Por qué el catálogo se pone lento al bajar?")
caja(s, 0.5, 1.05, 9.0, 0.5, f"Catálogo de 50.000 cursos, de 20 en 20. Pedir la página {n(int(PMAX), 0)} es pedir los últimos 20 cursos.", 14, AC5)
imagen(s, RES / "ppt-catalogo.png", 0.4, 1.55, w=5.2, h=3.4, marco=False)
for k, (tit, desc, color) in enumerate([
        ("Hoy: contar hoja por hoja", "Como buscar la página 500 de un libro contando desde el principio: la base cuenta y descarta los 49.980 cursos anteriores.", AC2),
        ("Nueva: un marcapáginas", "Recuerda el último curso que viste y sigue desde ahí. No cuenta nada: cualquier página cuesta lo mismo.", AC1)]):
    y = 1.6 + k * 1.65
    tarjeta(s, 5.9, y, 3.6, 1.5)
    caja(s, 6.1, y + 0.12, 3.25, 0.35, tit, 14, color, True)
    caja(s, 6.1, y + 0.52, 3.25, 0.95, desc, 12)

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
g.add_paragraph("Arquitectura de Software · Unidad 3 · Actividad 6 «Navegando mareas». Duración objetivo: " + TOTAL + " "
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
