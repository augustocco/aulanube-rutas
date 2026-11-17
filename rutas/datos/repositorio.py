"""Acceso a datos: dos implementaciones del mismo repositorio.

- RepositorioIngenuo (iteración 1): como trabaja hoy un LMS armado con
  plugins. Consulta lección por lección el avance del colaborador (patrón
  N+1), pagina el catálogo con OFFSET y cuenta el total en cada página.
- RepositorioOptimizado (iteración 2): consultas agrupadas, índices,
  paginación por llave (keyset) y caché a un lado (Cache-Aside) para la ruta
  y el árbol de cada curso.

Cada conexión cuenta las sentencias SQL que ejecuta, para mostrar en cada
respuesta cuántas consultas costó.
"""
from __future__ import annotations

import base64
import queue
import sqlite3
import threading
import time
from datetime import date

from rutas.dominio.contenido import Curso, Leccion, Modulo
from rutas.dominio.ruta import CursoPendiente

MIGRACION_V2 = """
CREATE INDEX IF NOT EXISTS ix_leccion_curso ON leccion(curso_id, modulo_id, orden);
CREATE INDEX IF NOT EXISTS ix_modulo_curso ON modulo(curso_id, orden);
CREATE INDEX IF NOT EXISTS ix_curso_titulo ON curso(titulo, id);
CREATE INDEX IF NOT EXISTS ix_curso_cat_titulo ON curso(categoria, titulo, id);
CREATE INDEX IF NOT EXISTS ix_matricula_colab ON matricula(colaborador_id);
ANALYZE;
"""


class Cache:
    """Caché en memoria con tiempo de vida (en producción sería Redis, compartida entre instancias)."""

    def __init__(self, ttl: float = 300.0):
        self.ttl = ttl
        self._datos: dict[str, tuple[float, object]] = {}
        self._candado = threading.Lock()
        self.aciertos = self.fallos = 0

    def obtener(self, clave: str, cargar):
        ahora = time.monotonic()
        with self._candado:
            v = self._datos.get(clave)
            if v and v[0] > ahora:
                self.aciertos += 1
                return v[1]
            self.fallos += 1
        valor = cargar()
        with self._candado:
            self._datos[clave] = (ahora + self.ttl, valor)
        return valor

    def borrar_prefijo(self, prefijo: str) -> None:
        with self._candado:
            for k in [k for k in self._datos if k.startswith(prefijo)]:
                del self._datos[k]

    def estado(self) -> dict:
        total = self.aciertos + self.fallos
        return {"entradas": len(self._datos), "aciertos": self.aciertos, "fallos": self.fallos,
                "tasa_aciertos": round(self.aciertos / total, 3) if total else None}


class Base:
    version = "?"

    def __init__(self, ruta_db: str):
        self.ruta_db = ruta_db
        self._local = threading.local()
        self.hoy = date.fromisoformat(self.con().execute("SELECT valor FROM meta WHERE clave='hoy'").fetchone()[0])

    def con(self) -> sqlite3.Connection:
        c = getattr(self._local, "con", None)
        if c is None:
            c = sqlite3.connect(self.ruta_db, check_same_thread=False, timeout=30)
            c.row_factory = sqlite3.Row
            c.execute("PRAGMA journal_mode=WAL")
            c.set_trace_callback(self._contar)
            self._local.con = c
            self._local.consultas = 0
        return c

    def _contar(self, sql: str) -> None:
        if not sql.startswith("PRAGMA"):
            self._local.consultas = getattr(self._local, "consultas", 0) + 1

    def reiniciar_conteo(self) -> None:
        self.con()
        self._local.consultas = 0

    @property
    def consultas(self) -> int:
        return getattr(self._local, "consultas", 0)

    # ----------------------------------------------------- comunes
    def colaborador(self, cid: int) -> dict:
        r = self.con().execute("SELECT * FROM colaborador WHERE id=?", (cid,)).fetchone()
        if r is None:
            raise KeyError(f"no existe el colaborador {cid}")
        return dict(r)

    def colaboradores(self, limite: int = 40) -> list[dict]:
        return [dict(r) for r in self.con().execute(
            "SELECT id, nombres, empresa, cargo FROM colaborador ORDER BY id LIMIT ?", (limite,))]

    def registrar_avance(self, cid: int, leccion_id: int) -> None:
        c = self.con()
        c.execute("INSERT OR IGNORE INTO avance VALUES (?,?,?)", (cid, leccion_id, self.hoy.isoformat()))
        c.commit()

    def curso_de_leccion(self, leccion_id: int) -> int:
        return self.con().execute("SELECT curso_id FROM leccion WHERE id=?", (leccion_id,)).fetchone()[0]

    def _dias(self, iso: str) -> int:
        return (date.fromisoformat(iso) - self.hoy).days


class RepositorioIngenuo(Base):
    version = "v1"

    def pendientes(self, cid: int) -> list[CursoPendiente]:
        c = self.con()
        res = []
        for m in c.execute("SELECT curso_id, fecha_limite, motivo FROM matricula WHERE colaborador_id=?",
                           (cid,)).fetchall():
            curso = c.execute("SELECT codigo, titulo FROM curso WHERE id=?", (m["curso_id"],)).fetchone()
            reqs = [r[0] for r in c.execute(
                "SELECT k.codigo FROM prerrequisito p JOIN curso k ON k.id=p.requiere_id WHERE p.curso_id=?",
                (m["curso_id"],))]
            pendientes = 0
            for lec in c.execute("SELECT id, duracion_min FROM leccion WHERE curso_id=?", (m["curso_id"],)).fetchall():
                hecha = c.execute("SELECT 1 FROM avance WHERE colaborador_id=? AND leccion_id=?",
                                  (cid, lec["id"])).fetchone()
                if not hecha:
                    pendientes += lec["duracion_min"]
            if pendientes:
                res.append(CursoPendiente(curso["codigo"], curso["titulo"], pendientes,
                                          self._dias(m["fecha_limite"]), m["motivo"], frozenset(reqs)))
        return res

    def arbol(self, curso_id: int) -> Curso:
        c = self.con()
        k = c.execute("SELECT id, titulo FROM curso WHERE id=?", (curso_id,)).fetchone()
        curso = Curso(k["id"], k["titulo"])
        for m in c.execute("SELECT id, titulo FROM modulo WHERE curso_id=? ORDER BY orden", (curso_id,)).fetchall():
            mod = Modulo(m["id"], m["titulo"])
            for l in c.execute("SELECT id, titulo, duracion_min FROM leccion WHERE modulo_id=? ORDER BY orden",
                               (m["id"],)).fetchall():
                mod.agregar(Leccion(l["id"], l["titulo"], l["duracion_min"]))
            curso.agregar(mod)
        return curso

    def completadas(self, cid: int, curso: Curso) -> set[int]:
        c = self.con()
        return {l.id for l in curso.lecciones()
                if c.execute("SELECT 1 FROM avance WHERE colaborador_id=? AND leccion_id=?", (cid, l.id)).fetchone()}

    def id_curso(self, codigo: str) -> int:
        return self.con().execute("SELECT id FROM curso WHERE codigo=?", (codigo,)).fetchone()[0]

    def catalogo(self, categoria: str = "", q: str = "", pagina: int = 1, despues: str = "", tam: int = 20) -> dict:
        c = self.con()
        filtro, args = ["1=1"], []
        if categoria:
            filtro.append("categoria=?"); args.append(categoria)
        if q:
            filtro.append("titulo LIKE ?"); args.append(f"%{q}%")
        where = " AND ".join(filtro)
        total = c.execute(f"SELECT COUNT(*) FROM curso WHERE {where}", args).fetchone()[0]
        filas = c.execute(f"SELECT id, codigo, titulo, categoria, duracion_min FROM curso WHERE {where} "
                          f"ORDER BY titulo, id LIMIT ? OFFSET ?", [*args, tam, (pagina - 1) * tam]).fetchall()
        return {"cursos": [dict(f) for f in filas], "total": total, "pagina": pagina,
                "siguiente": str(pagina + 1) if pagina * tam < total else None}


class RepositorioOptimizado(Base):
    version = "v2"

    def __init__(self, ruta_db: str, cache: Cache):
        super().__init__(ruta_db)
        self.cache = cache
        self.con().executescript(MIGRACION_V2)

    def pendientes(self, cid: int) -> list[CursoPendiente]:
        c = self.con()
        filas = c.execute("""
            SELECT k.id, k.codigo, k.titulo, m.fecha_limite, m.motivo,
                   SUM(CASE WHEN a.leccion_id IS NULL THEN l.duracion_min ELSE 0 END) AS pendientes
            FROM matricula m
            JOIN curso k ON k.id = m.curso_id
            JOIN leccion l ON l.curso_id = k.id
            LEFT JOIN avance a ON a.colaborador_id = m.colaborador_id AND a.leccion_id = l.id
            WHERE m.colaborador_id = ?
            GROUP BY k.id""", (cid,)).fetchall()
        ids = [f["id"] for f in filas]
        reqs: dict[int, list[str]] = {}
        if ids:
            marcas = ",".join("?" * len(ids))
            for r in c.execute(f"SELECT p.curso_id, k.codigo FROM prerrequisito p JOIN curso k ON k.id=p.requiere_id "
                               f"WHERE p.curso_id IN ({marcas})", ids):
                reqs.setdefault(r[0], []).append(r[1])
        return [CursoPendiente(f["codigo"], f["titulo"], f["pendientes"], self._dias(f["fecha_limite"]), f["motivo"],
                               frozenset(reqs.get(f["id"], []))) for f in filas if f["pendientes"]]

    def arbol(self, curso_id: int) -> Curso:
        def cargar():
            c = self.con()
            curso = None
            modulos: dict[int, Modulo] = {}
            for r in c.execute("""
                    SELECT k.id kid, k.titulo kt, m.id mid, m.titulo mt, l.id lid, l.titulo lt, l.duracion_min d
                    FROM curso k JOIN modulo m ON m.curso_id=k.id JOIN leccion l ON l.modulo_id=m.id
                    WHERE k.id=? ORDER BY m.orden, l.orden""", (curso_id,)):
                curso = curso or Curso(r["kid"], r["kt"])
                if r["mid"] not in modulos:
                    modulos[r["mid"]] = Modulo(r["mid"], r["mt"])
                    curso.agregar(modulos[r["mid"]])
                modulos[r["mid"]].agregar(Leccion(r["lid"], r["lt"], r["d"]))
            return curso
        return self.cache.obtener(f"curso:{curso_id}", cargar)  # el contenido casi no cambia

    def completadas(self, cid: int, curso: Curso) -> set[int]:
        return {r[0] for r in self.con().execute(
            "SELECT a.leccion_id FROM avance a JOIN leccion l ON l.id=a.leccion_id "
            "WHERE a.colaborador_id=? AND l.curso_id=?", (cid, curso.id))}

    def id_curso(self, codigo: str) -> int:
        return self.cache.obtener(f"codigo:{codigo}", lambda: self.con().execute(
            "SELECT id FROM curso WHERE codigo=?", (codigo,)).fetchone()[0])

    def catalogo(self, categoria: str = "", q: str = "", pagina: int = 1, despues: str = "", tam: int = 20) -> dict:
        c = self.con()
        filtro, args = ["1=1"], []
        if categoria:
            filtro.append("categoria=?"); args.append(categoria)
        if q:
            filtro.append("titulo LIKE ?"); args.append(f"%{q}%")
        base = " AND ".join(filtro)
        # El total se calcula una vez por filtro y se reutiliza (Cache-Aside con vencimiento).
        total = self.cache.obtener(f"total:{categoria}|{q}", lambda: c.execute(
            f"SELECT COUNT(*) FROM curso WHERE {base}", args).fetchone()[0])
        where, args2 = base, list(args)
        if despues:  # paginación por llave: continúa después del último curso visto
            titulo, ident = leer_cursor(despues)
            where += " AND (titulo, id) > (?, ?)"
            args2 += [titulo, ident]
        filas = c.execute(f"SELECT id, codigo, titulo, categoria, duracion_min FROM curso WHERE {where} "
                          f"ORDER BY titulo, id LIMIT ?", [*args2, tam + 1]).fetchall()
        hay_mas = len(filas) > tam  # se pide una fila de más para saber si existe otra página
        filas = filas[:tam]
        sig = crear_cursor(filas[-1]["titulo"], filas[-1]["id"]) if hay_mas else None
        return {"cursos": [dict(f) for f in filas], "total": total, "siguiente": sig}


def crear_cursor(titulo: str, ident: int) -> str:
    """Cursor opaco y seguro para URL con la llave del último curso de la página."""
    return base64.urlsafe_b64encode(f"{titulo}|{ident}".encode("utf-8")).decode("ascii").rstrip("=")


def leer_cursor(cursor: str) -> tuple[str, int]:
    crudo = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)).decode("utf-8")
    titulo, _, ident = crudo.rpartition("|")
    return titulo, int(ident)


class RepositorioAsincrono(RepositorioOptimizado):
    """Iteración 3: el avance se guarda en lotes, en segundo plano.

    Las pruebas de carga de la iteración 2 mostraron que el cuello de botella
    pasó a la escritura: SQLite admite un solo escritor y cada «completar»
    esperaba su propia confirmación en disco. Ahora «completar» deja el avance
    en una cola y responde; un hilo escritor lo guarda cada 100 ms en una sola
    transacción (nivelación de carga basada en cola).

    Para que el colaborador vea su propio avance de inmediato (leer lo que uno
    mismo escribió), las lecturas suman lo que aún está en la cola.
    Costo aceptado: si el proceso se cae, se pueden perder hasta 100 ms de avance.
    """

    version = "v3"
    VENTANA = 0.1

    def __init__(self, ruta_db: str, cache: Cache):
        super().__init__(ruta_db, cache)
        self._cola: "queue.Queue[tuple[int, int, str]]" = queue.Queue()
        self._pendiente: dict[int, dict[int, int]] = {}   # colaborador -> {lección: curso}
        self._candado = threading.Lock()
        self.lotes = self.escritos = 0
        threading.Thread(target=self._escribir, name="escritor-avance", daemon=True).start()

    def _curso_y_duracion(self, leccion_id: int) -> tuple[int, int, str]:
        return self.cache.obtener(f"leccion:{leccion_id}", lambda: tuple(self.con().execute(
            "SELECT l.curso_id, l.duracion_min, k.codigo FROM leccion l JOIN curso k ON k.id=l.curso_id "
            "WHERE l.id=?", (leccion_id,)).fetchone()))

    def curso_de_leccion(self, leccion_id: int) -> int:
        return self._curso_y_duracion(leccion_id)[0]

    def registrar_avance(self, cid: int, leccion_id: int) -> None:
        curso_id = self._curso_y_duracion(leccion_id)[0]
        with self._candado:
            self._pendiente.setdefault(cid, {})[leccion_id] = curso_id
        self._cola.put((cid, leccion_id, self.hoy.isoformat()))

    def _escribir(self) -> None:
        c = sqlite3.connect(self.ruta_db, check_same_thread=False, timeout=30)
        c.execute("PRAGMA journal_mode=WAL")
        while True:
            lote = [self._cola.get()]
            time.sleep(self.VENTANA)          # junta lo que llegue en la ventana
            while True:
                try:
                    lote.append(self._cola.get_nowait())
                except queue.Empty:
                    break
            c.executemany("INSERT OR IGNORE INTO avance VALUES (?,?,?)", lote)
            c.commit()                         # una sola confirmación en disco por lote
            with self._candado:
                for cid, lid, _ in lote:
                    self._pendiente.get(cid, {}).pop(lid, None)
                self.lotes += 1
                self.escritos += len(lote)

    def _en_cola(self, cid: int) -> dict[int, int]:
        with self._candado:
            return dict(self._pendiente.get(cid, {}))

    def completadas(self, cid: int, curso: Curso) -> set[int]:
        return super().completadas(cid, curso) | {l for l, k in self._en_cola(cid).items() if k == curso.id}

    def pendientes(self, cid: int) -> list[CursoPendiente]:
        en_cola = self._en_cola(cid)   # se toma antes de leer la base
        if not en_cola:
            return super().pendientes(cid)
        c = self.con()
        c.execute("BEGIN")             # mismo instante de la base para las dos lecturas (WAL)
        try:
            base = super().pendientes(cid)
            marcas = ",".join("?" * len(en_cola))
            ya = {r[0] for r in c.execute(f"SELECT leccion_id FROM avance WHERE colaborador_id=? "
                                          f"AND leccion_id IN ({marcas})", [cid, *en_cola])}
        finally:
            c.execute("COMMIT")
        restar: dict[str, int] = {}
        for lid in en_cola:
            if lid not in ya:
                _, dur, codigo = self._curso_y_duracion(lid)
                restar[codigo] = restar.get(codigo, 0) + dur
        res = []
        for p in base:
            m = p.minutos_pendientes - restar.get(p.codigo, 0)
            if m > 0:
                res.append(CursoPendiente(p.codigo, p.titulo, m, p.vence_en_dias, p.motivo, p.prerrequisitos))
        return res
