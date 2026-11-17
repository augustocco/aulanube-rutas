"""Ruta de formación de un colaborador: patrón Strategy.

Cada estrategia devuelve un orden de preferencia de los cursos pendientes. El
plan que se muestra se obtiene siempre igual: el colaborador estudia sus
minutos diarios y toma el primer curso de su lista que ya esté disponible (sus
prerrequisitos terminados). Así las tres estrategias se comparan en igualdad.

- OrdenAlfabetico: lo que hace hoy la página «Mis cursos» (iteración 1).
- PorFechaLimite: primero lo que vence antes, sin mirar prerrequisitos.
- PorUrgencia: fecha límite efectiva, que hereda la urgencia del curso que
  depende de él (EDF con precedencias), y orden topológico (iteración 2).
"""
from __future__ import annotations

import heapq
import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(frozen=True)
class CursoPendiente:
    codigo: str
    titulo: str
    minutos_pendientes: int
    vence_en_dias: int          # fecha límite (cierre de campaña o vencimiento del certificado)
    motivo: str = "campaña"     # «campaña» o «vencimiento»
    prerrequisitos: frozenset = field(default_factory=frozenset)


@dataclass
class ItemRuta:
    orden: int
    codigo: str
    titulo: str
    motivo: str
    vence_en_dias: int
    inicia_dia: int
    termina_dia: int
    a_tiempo: bool
    bloqueado_por: list[str]
    minutos_pendientes: int


class EstrategiaRuta(ABC):
    nombre = "abstracta"
    descripcion = ""

    @abstractmethod
    def preferencia(self, cursos: list[CursoPendiente], minutos_dia: int) -> list[str]:
        """Orden de preferencia de los códigos de curso."""


class OrdenAlfabetico(EstrategiaRuta):
    nombre = "alfabetico"
    descripcion = "Orden alfabético (página «Mis cursos» actual)"

    def preferencia(self, cursos, minutos_dia):
        return [c.codigo for c in sorted(cursos, key=lambda c: c.titulo)]


class PorFechaLimite(EstrategiaRuta):
    nombre = "fecha"
    descripcion = "Primero lo que vence antes"

    def preferencia(self, cursos, minutos_dia):
        return [c.codigo for c in sorted(cursos, key=lambda c: (c.vence_en_dias, c.titulo))]


class PorUrgencia(EstrategiaRuta):
    nombre = "urgencia"
    descripcion = "Urgencia con prerrequisitos (fecha límite efectiva)"

    def preferencia(self, cursos, minutos_dia):
        por_codigo = {c.codigo: c for c in cursos}
        dias = {c.codigo: math.ceil(c.minutos_pendientes / minutos_dia) for c in cursos}
        dependientes: dict[str, list[str]] = {c.codigo: [] for c in cursos}
        faltan: dict[str, int] = {}
        for c in cursos:
            reqs = [r for r in c.prerrequisitos if r in por_codigo]
            faltan[c.codigo] = len(reqs)
            for r in reqs:
                dependientes[r].append(c.codigo)
        orden_topo = _topologico(cursos, dependientes, faltan, clave=lambda k: por_codigo[k].titulo)
        # Fecha límite efectiva: un prerrequisito debe terminar a tiempo para que
        # el curso que depende de él alcance a hacerse (se recorre al revés).
        efectiva = {k: por_codigo[k].vence_en_dias for k in por_codigo}
        for k in reversed(orden_topo):
            for d in dependientes[k]:
                efectiva[k] = min(efectiva[k], efectiva[d] - dias[d])
        return _topologico(cursos, dependientes, faltan,
                           clave=lambda k: (efectiva[k], por_codigo[k].vence_en_dias, por_codigo[k].titulo))


def _topologico(cursos, dependientes, faltan, clave) -> list[str]:
    """Algoritmo de Kahn con cola de prioridad: entre los disponibles, el de menor clave."""
    faltan = dict(faltan)
    listos = [(clave(c.codigo), c.codigo) for c in cursos if faltan[c.codigo] == 0]
    heapq.heapify(listos)
    orden = []
    while listos:
        _, k = heapq.heappop(listos)
        orden.append(k)
        for d in dependientes[k]:
            faltan[d] -= 1
            if faltan[d] == 0:
                heapq.heappush(listos, (clave(d), d))
    if len(orden) != len(cursos):
        raise ValueError("los prerrequisitos forman un ciclo")
    return orden


def planificar(cursos: list[CursoPendiente], estrategia: EstrategiaRuta, minutos_dia: int) -> list[ItemRuta]:
    """Simula el estudio siguiendo la preferencia y estima cuándo termina cada curso."""
    por_codigo = {c.codigo: c for c in cursos}
    preferencia = estrategia.preferencia(cursos, minutos_dia)
    hechos: set[str] = set()
    minutos = 0
    plan: list[ItemRuta] = []
    pendientes = list(preferencia)
    while pendientes:
        disponible = next((k for k in pendientes
                           if all(r in hechos or r not in por_codigo for r in por_codigo[k].prerrequisitos)), None)
        if disponible is None:
            raise ValueError("ningún curso disponible: prerrequisito fuera de la ruta")
        c = por_codigo[disponible]
        inicio = minutos // minutos_dia
        minutos += c.minutos_pendientes
        fin = math.ceil(minutos / minutos_dia)
        plan.append(ItemRuta(len(plan) + 1, c.codigo, c.titulo, c.motivo, c.vence_en_dias, inicio, fin,
                             fin <= c.vence_en_dias, [], c.minutos_pendientes))
        hechos.add(disponible)
        pendientes.remove(disponible)
    # El colaborador ve la lista en el orden de la estrategia; se marca lo que hoy está bloqueado.
    for item in plan:
        item.bloqueado_por = sorted(r for r in por_codigo[item.codigo].prerrequisitos if r in por_codigo)
    orden_visible = {k: i for i, k in enumerate(preferencia)}
    plan.sort(key=lambda it: orden_visible[it.codigo])
    for i, item in enumerate(plan, 1):
        item.orden = i
    return plan


ESTRATEGIAS: dict[str, EstrategiaRuta] = {e.nombre: e for e in (OrdenAlfabetico(), PorFechaLimite(), PorUrgencia())}
