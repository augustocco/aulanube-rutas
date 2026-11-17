"""Servidor HTTP de AulaNube Rutas.

    python -m rutas.servidor --version v2 --db rutas.db --puerto 7400
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

from rutas.comun.red import Enrutador, Respuesta, crear_servidor
from rutas.servicio import ServicioNavegacion

VISTA = Path(__file__).parent / "vista" / "index.html"


def construir(s: ServicioNavegacion) -> Enrutador:
    r = Enrutador()

    def medido(funcion):
        def envoltura(sol):
            s.repo.reiniciar_conteo()
            t0 = time.perf_counter()
            datos = funcion(sol)
            ms = round((time.perf_counter() - t0) * 1000, 2)
            cab = {"X-Consultas": str(s.repo.consultas), "X-Tiempo-ms": str(ms), "X-Version": s.version}
            if isinstance(datos, Respuesta):
                datos.cabeceras.update(cab)
                return datos
            return Respuesta(200, {**datos, "_medicion": {"ms": ms, "consultas": s.repo.consultas,
                                                           "version": s.version}}, cabeceras=cab)
        return envoltura

    @r.ruta("GET", "/")
    def vista(sol):
        return Respuesta(200, VISTA.read_text(encoding="utf-8"), "text/html")

    @r.ruta("GET", "/api/estado")
    def estado(sol):
        escritura = ({"lotes": s.repo.lotes, "escritos": s.repo.escritos} if s.version == "v3" else None)
        return {"version": s.version, "estrategia": s.estrategia_defecto, "cache": s.cache.estado(),
                "escritura_por_lotes": escritura,
                "eventos": s.bitacora.eventos[-10:]}

    @r.ruta("GET", "/api/colaboradores")
    def colaboradores(sol):
        return {"colaboradores": s.repo.colaboradores()}

    @r.ruta("GET", "/api/colaboradores/{cid}/ruta")
    @medido
    def ruta(sol):
        return s.ruta(int(sol.parametros["cid"]), sol.consulta.get("estrategia") or None)

    @r.ruta("GET", "/api/colaboradores/{cid}/continuar")
    @medido
    def continuar(sol):
        return s.continuar(int(sol.parametros["cid"]))

    @r.ruta("GET", "/api/colaboradores/{cid}/lecciones/{lid}")
    @medido
    def leccion(sol):
        return s.leccion(int(sol.parametros["cid"]), int(sol.parametros["lid"]))

    @r.ruta("POST", "/api/colaboradores/{cid}/lecciones/{lid}/completar")
    @medido
    def completar(sol):
        return s.completar(int(sol.parametros["cid"]), int(sol.parametros["lid"]))

    @r.ruta("GET", "/api/catalogo")
    @medido
    def catalogo(sol):
        q = sol.consulta
        return s.repo.catalogo(q.get("categoria", ""), q.get("q", ""), int(q.get("pagina", 1) or 1),
                               q.get("despues", ""))

    return r


def main() -> None:
    p = argparse.ArgumentParser(description="AulaNube Rutas")
    p.add_argument("--version", choices=["v1", "v2", "v3"], default="v3")
    p.add_argument("--db", default="rutas.db")
    p.add_argument("--puerto", type=int, default=7400)
    a = p.parse_args()
    if not Path(a.db).exists():
        from rutas.datos.semilla import crear
        print("Creando la base de demostración…", flush=True)
        crear(Path(a.db))
    servicio = ServicioNavegacion(a.db, a.version)
    print(f"[rutas] {a.version} en http://127.0.0.1:{a.puerto}", flush=True)
    crear_servidor("0.0.0.0", a.puerto, construir(servicio)).serve_forever()


if __name__ == "__main__":
    main()
