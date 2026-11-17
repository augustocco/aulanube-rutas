"""Servicio de navegación: arma la ruta, resuelve «Continuar» y mueve al
colaborador entre lecciones. Es la misma lógica para las dos iteraciones; lo
que cambia es el repositorio, la estrategia por defecto y la caché.

El servicio no guarda estado de navegación entre solicitudes (el historial
«Atrás» vive en el navegador, patrón Command), así que se pueden poner varias
instancias detrás de un balanceador.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import timedelta

from rutas.datos.repositorio import Cache, RepositorioAsincrono, RepositorioIngenuo, RepositorioOptimizado
from rutas.dominio.contenido import IteradorPendientes, vecinas
from rutas.dominio.eventos import Bitacora, InvalidadorRuta, Publicador
from rutas.dominio.ruta import ESTRATEGIAS, planificar


class ServicioNavegacion:
    def __init__(self, ruta_db: str, version: str = "v2"):
        self.version = version
        self.cache = Cache(ttl=300)
        self.eventos = Publicador()
        self.bitacora = Bitacora()
        self.eventos.suscribir(self.bitacora)
        if version == "v1":
            self.repo = RepositorioIngenuo(ruta_db)
            self.estrategia_defecto = "alfabetico"
        else:
            clase = RepositorioAsincrono if version == "v3" else RepositorioOptimizado
            self.repo = clase(ruta_db, self.cache)
            self.estrategia_defecto = "urgencia"
            self.eventos.suscribir(InvalidadorRuta(self.cache))

    # ------------------------------------------------------------- ruta
    def _plan(self, cid: int, estrategia: str):
        colab = self.repo.colaborador(cid)
        plan = planificar(self.repo.pendientes(cid), ESTRATEGIAS[estrategia], colab["minutos_dia"])
        return colab, plan

    def ruta(self, cid: int, estrategia: str | None = None) -> dict:
        estrategia = estrategia or self.estrategia_defecto
        if self.version != "v1":
            colab, plan = self.cache.obtener(f"c{cid}:ruta:{estrategia}", lambda: self._plan(cid, estrategia))
        else:
            colab, plan = self._plan(cid, estrategia)
        hoy = self.repo.hoy
        items = []
        for it in plan:
            d = asdict(it)
            d["fecha_limite"] = (hoy + timedelta(days=it.vence_en_dias)).isoformat()
            d["termina_estimado"] = (hoy + timedelta(days=it.termina_dia)).isoformat()
            items.append(d)
        obligatorios = [i for i in items if i["motivo"] != "voluntario"]
        return {"colaborador": colab, "estrategia": estrategia, "items": items,
                "resumen": {"cursos": len(items), "obligatorios": len(obligatorios),
                            "a_tiempo": sum(i["a_tiempo"] for i in obligatorios),
                            "tarde": sum(not i["a_tiempo"] for i in obligatorios)}}

    # -------------------------------------------------------- continuar
    def continuar(self, cid: int) -> dict:
        r = self.ruta(cid)
        for item in r["items"]:  # el primer curso de la ruta sin prerrequisitos pendientes
            if not item["bloqueado_por"]:
                return {**self._en_curso(cid, self.repo.id_curso(item["codigo"]), None),
                        "curso_ruta": item["codigo"]}
        return {"terminado": True}

    def leccion(self, cid: int, leccion_id: int) -> dict:
        return self._en_curso(cid, self.repo.curso_de_leccion(leccion_id), leccion_id)

    def _en_curso(self, cid: int, curso_id: int, leccion_id: int | None) -> dict:
        curso = self.repo.arbol(curso_id)
        completadas = self.repo.completadas(cid, curso)
        if leccion_id is None:
            leccion = IteradorPendientes(curso, completadas).siguiente()
            leccion_id = leccion.id if leccion else next(curso.lecciones()).id
        anterior, siguiente = vecinas(curso, leccion_id)
        pendiente = IteradorPendientes(curso, completadas, desde=leccion_id)
        proxima = next((l for l in pendiente if l.id != leccion_id), None)
        actual = next(l for l in curso.lecciones() if l.id == leccion_id)
        total = sum(1 for _ in curso.lecciones())
        return {"curso": {"id": curso.id, "titulo": curso.titulo,
                          "modulos": [{"titulo": m.titulo, "lecciones": [
                              {"id": l.id, "titulo": l.titulo, "completada": l.id in completadas}
                              for l in m.lecciones()]} for m in curso.hijos]},
                "leccion": {"id": actual.id, "titulo": actual.titulo, "duracion_min": actual.duracion_min,
                            "completada": actual.id in completadas},
                "anterior": anterior, "siguiente": siguiente, "proxima_pendiente": proxima.id if proxima else None,
                "progreso": round(100 * len(completadas) / total, 1),
                "minutos_pendientes": curso.minutos_pendientes(completadas)}

    def completar(self, cid: int, leccion_id: int) -> dict:
        self.repo.registrar_avance(cid, leccion_id)
        self.eventos.publicar("leccion.completada", {"colaborador": cid, "leccion": leccion_id})
        return self.leccion(cid, leccion_id)
