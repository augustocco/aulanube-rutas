"""Evaluación de AulaNube Rutas: iteración 1 (v1) frente a iteración 2 (v2).

E1 · Efectividad de la ruta: con los 2.000 colaboradores, ¿qué porcentaje de
     cursos obligatorios termina antes de su fecha límite con cada estrategia?
E2 · Prueba de carga: usuarios virtuales concurrentes recorren el flujo de
     navegación (ruta, continuar, completar, catálogo) contra el servidor real.
E3 · Catálogo profundo: latencia de la página N con OFFSET y con keyset, en un
     catálogo de 50.000 cursos.

    python scripts/evaluar.py            # todo
    python scripts/evaluar.py E2         # solo uno
"""
from __future__ import annotations

import json
import random
import shutil
import statistics
import subprocess
import sys
import threading
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from rutas.comun.red import ClienteHTTP, ErrorRed  # noqa: E402
from rutas.datos.repositorio import Cache, RepositorioIngenuo, RepositorioOptimizado, crear_cursor  # noqa: E402
from rutas.datos.semilla import crear  # noqa: E402
from rutas.dominio.ruta import ESTRATEGIAS, planificar  # noqa: E402

RES = RAIZ / "docs" / "resultados"
TRABAJO = RAIZ / "registros"
BASE = TRABAJO / "base.db"
GRANDE = TRABAJO / "grande.db"
SALIDA = RES / "resultados.json"
APDEX_T = 0.2           # segundos; elegido antes de medir (navegación interactiva)
CONCURRENCIA = [1, 10, 25, 50]
DURACION = 20           # segundos por nivel de concurrencia


def p(valores, q):
    if not valores:
        return None
    v = sorted(valores)
    return v[min(len(v) - 1, int(round(q / 100 * len(v) + 0.5)) - 1)]


def apdex(lat):
    sat = sum(1 for x in lat if x <= APDEX_T)
    tol = sum(1 for x in lat if APDEX_T < x <= 4 * APDEX_T)
    return round((sat + tol / 2) / len(lat), 3) if lat else None


# ------------------------------------------------------------------ E1
def e1() -> dict:
    repo = RepositorioOptimizado(str(_copia("e1")), Cache())
    filas = repo.con().execute("SELECT id, minutos_dia FROM colaborador").fetchall()
    res = {}
    for nombre, est in ESTRATEGIAS.items():
        cursos = a_tiempo = colab_ok = 0
        sub_cursos = sub_a_tiempo = 0  # vencimiento con prerrequisito pendiente
        atrasos = []
        primero_obligatorio = 0
        for f in filas:
            pend = repo.pendientes(f["id"])
            if not pend:
                continue
            plan = planificar(pend, est, f["minutos_dia"])
            oblig = [i for i in plan if i.motivo != "voluntario"]
            cursos += len(oblig)
            a_tiempo += sum(i.a_tiempo for i in oblig)
            colab_ok += all(i.a_tiempo for i in oblig)
            atrasos += [i.termina_dia - i.vence_en_dias for i in oblig if not i.a_tiempo]
            criticos = [i for i in oblig if i.motivo == "vencimiento" and i.bloqueado_por]
            sub_cursos += len(criticos)
            sub_a_tiempo += sum(i.a_tiempo for i in criticos)
            disponibles = [i for i in plan if not i.bloqueado_por]
            primero_obligatorio += bool(disponibles) and disponibles[0].motivo != "voluntario"
        res[nombre] = {"descripcion": est.descripcion, "cursos_obligatorios": cursos,
                       "a_tiempo_pct": round(100 * a_tiempo / cursos, 1),
                       "colaboradores_al_dia_pct": round(100 * colab_ok / len(filas), 1),
                       "atraso_medio_dias": round(statistics.mean(atrasos), 1) if atrasos else 0,
                       "vencimientos_con_prerrequisito": sub_cursos,
                       "vencimientos_con_prerrequisito_a_tiempo_pct": round(100 * sub_a_tiempo / sub_cursos, 1) if sub_cursos else None,
                       "continuar_lleva_a_obligatorio_pct": round(100 * primero_obligatorio / len(filas), 1)}
        print("E1", nombre, res[nombre], flush=True)
    return res


# ------------------------------------------------------------------ E2
def _copia(etiqueta: str) -> Path:
    destino = TRABAJO / f"{etiqueta}.db"
    for sufijo in ("", "-wal", "-shm"):
        Path(str(destino) + sufijo).unlink(missing_ok=True)
    shutil.copy(BASE, destino)
    return destino


def _servidor(version: str, puerto: int) -> subprocess.Popen:
    db = _copia(f"carga-{version}")
    proc = subprocess.Popen([sys.executable, "-m", "rutas.servidor", "--version", version, "--db", str(db),
                             "--puerto", str(puerto)], cwd=RAIZ, stdout=subprocess.DEVNULL,
                            stderr=subprocess.STDOUT)
    c = ClienteHTTP(f"http://127.0.0.1:{puerto}")
    for _ in range(100):
        try:
            c.llamar("GET", "/api/estado")
            return proc
        except ErrorRed:
            time.sleep(0.1)
    raise RuntimeError("el servidor no arrancó")


def _usuario(url, fin, version, registro, semilla):
    azar = random.Random(semilla)
    c = ClienteHTTP(url, tiempo_espera=60)

    def medir(tipo, metodo, ruta):
        t0 = time.perf_counter()
        try:
            r = c.llamar(metodo, ruta)
            registro.append((tipo, time.perf_counter() - t0, r.get("_medicion", {}).get("consultas", 0), True))
            return r
        except ErrorRed:
            registro.append((tipo, time.perf_counter() - t0, 0, False))
            return {}

    while time.time() < fin:
        cid = azar.randint(1, 2000)
        medir("ruta", "GET", f"/api/colaboradores/{cid}/ruta")
        d = medir("continuar", "GET", f"/api/colaboradores/{cid}/continuar")
        if d.get("leccion"):
            medir("completar", "POST", f"/api/colaboradores/{cid}/lecciones/{d['leccion']['id']}/completar")
        # Catálogo: abre y baja varias páginas, como quien busca un curso electivo.
        k = medir("catalogo", "GET", "/api/catalogo")
        for _ in range(azar.randint(1, 15)):
            sig = k.get("siguiente")
            if not sig or time.time() >= fin:
                break
            q = f"pagina={sig}" if version == "v1" else f"despues={sig}"
            k = medir("catalogo", "GET", f"/api/catalogo?{q}")


def e2() -> dict:
    res = {}
    for version, puerto in (("v1", 7411), ("v2", 7412), ("v3", 7413)):
        proc = _servidor(version, puerto)
        try:
            res[version] = {}
            for n in CONCURRENCIA:
                registro: list = []
                fin = time.time() + DURACION
                hilos = [threading.Thread(target=_usuario, args=(f"http://127.0.0.1:{puerto}", fin, version,
                                                                 registro, 1000 * n + i)) for i in range(n)]
                t0 = time.time()
                for h in hilos:
                    h.start()
                for h in hilos:
                    h.join()
                dur = time.time() - t0
                todos = [x[1] for x in registro if x[3]]
                por_tipo = {}
                for tipo in ("ruta", "continuar", "completar", "catalogo"):
                    lat = [x[1] for x in registro if x[0] == tipo and x[3]]
                    q = [x[2] for x in registro if x[0] == tipo and x[3]]
                    por_tipo[tipo] = {"n": len(lat), "apdex": apdex(lat), "p50_ms": round(1000 * p(lat, 50), 1),
                                      "p95_ms": round(1000 * p(lat, 95), 1),
                                      "consultas_media": round(statistics.mean(q), 1) if q else 0}
                res[version][n] = {"solicitudes": len(registro), "errores": sum(1 for x in registro if not x[3]),
                                   "rps": round(len(todos) / dur, 1), "p50_ms": round(1000 * p(todos, 50), 1),
                                   "p95_ms": round(1000 * p(todos, 95), 1), "p99_ms": round(1000 * p(todos, 99), 1),
                                   "apdex": apdex(todos), "por_tipo": por_tipo}
                print("E2", version, n, {k: v for k, v in res[version][n].items() if k != "por_tipo"}, flush=True)
        finally:
            proc.kill()
            proc.wait()
    return res


# ------------------------------------------------------------------ E3
def e3() -> dict:
    if not GRANDE.exists():
        crear(GRANDE, cursos=50_000, colaboradores=200)
    v1 = RepositorioIngenuo(str(GRANDE))
    v2 = RepositorioOptimizado(str(_copia_grande()), Cache(ttl=1e9))
    paginas = [1, 10, 100, 500, 1000, 2500]
    res = {"v1": {}, "v2": {}}
    orden = [(r["titulo"], r["id"]) for r in v2.con().execute("SELECT titulo, id FROM curso ORDER BY titulo, id")]
    for pag in paginas:
        cursor = "" if pag == 1 else crear_cursor(*orden[(pag - 1) * 20 - 1])
        for nombre, llamar in (("v1", lambda: v1.catalogo(pagina=pag)), ("v2", lambda: v2.catalogo(despues=cursor))):
            llamar()
            tiempos = []
            for _ in range(15):
                t0 = time.perf_counter()
                k = llamar()
                tiempos.append(time.perf_counter() - t0)
            res[nombre][pag] = round(1000 * statistics.median(tiempos), 2)
            assert k["cursos"][0]["id"] == orden[(pag - 1) * 20][1], "las dos versiones deben devolver la misma página"
        print("E3 página", pag, res["v1"][pag], res["v2"][pag], flush=True)
    return res


def _copia_grande() -> Path:
    destino = TRABAJO / "grande-v2.db"
    if not destino.exists():
        shutil.copy(GRANDE, destino)
    return destino


def main() -> None:
    TRABAJO.mkdir(exist_ok=True)
    RES.mkdir(parents=True, exist_ok=True)
    if not BASE.exists():
        crear(BASE)
    elegidos = sys.argv[1:] or ["E1", "E2", "E3"]
    datos = json.loads(SALIDA.read_text(encoding="utf-8")) if SALIDA.exists() else {}
    for e in elegidos:
        datos[e] = {"E1": e1, "E2": e2, "E3": e3}[e]()
        datos["apdex_t_s"] = APDEX_T
        SALIDA.write_text(json.dumps(datos, indent=1, ensure_ascii=False), encoding="utf-8")
    print("Resultados en", SALIDA)


if __name__ == "__main__":
    main()
