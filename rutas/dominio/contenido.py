"""Estructura del contenido de un curso: patrones Composite e Iterator.

Composite: un Curso contiene Módulos y un Módulo contiene Lecciones. Los tres
responden la misma pregunta («¿cuántos minutos te faltan?») sin que quien
pregunta sepa si habla con una hoja o con un compuesto.

Iterator: recorre el árbol en el orden en que se estudia (preorden) y sabe
saltarse lo ya completado. La navegación «Continuar» no conoce la forma del
árbol; solo pide «la siguiente lección pendiente».
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Iterator


class NodoContenido(ABC):
    titulo: str

    @abstractmethod
    def lecciones(self) -> Iterator["Leccion"]:
        """Recorre las hojas en el orden de estudio."""

    def minutos_pendientes(self, completadas: set[int]) -> int:
        return sum(l.duracion_min for l in self.lecciones() if l.id not in completadas)

    def minutos_totales(self) -> int:
        return sum(l.duracion_min for l in self.lecciones())


@dataclass
class Leccion(NodoContenido):
    id: int
    titulo: str
    duracion_min: int

    def lecciones(self):
        yield self


@dataclass
class Compuesto(NodoContenido):
    id: int
    titulo: str
    hijos: list[NodoContenido] = field(default_factory=list)

    def agregar(self, hijo: NodoContenido) -> None:
        self.hijos.append(hijo)

    def lecciones(self):
        for h in self.hijos:
            yield from h.lecciones()


class Modulo(Compuesto):
    pass


class Curso(Compuesto):
    pass


class IteradorPendientes:
    """Iterador sobre las lecciones no completadas, desde una posición dada."""

    def __init__(self, raiz: NodoContenido, completadas: set[int], desde: int | None = None):
        self._lecciones = list(raiz.lecciones())
        self._completadas = completadas
        self._pos = 0
        if desde is not None:
            for i, l in enumerate(self._lecciones):
                if l.id == desde:
                    self._pos = i
                    break

    def __iter__(self):
        return self

    def __next__(self) -> Leccion:
        while self._pos < len(self._lecciones):
            l = self._lecciones[self._pos]
            self._pos += 1
            if l.id not in self._completadas:
                return l
        raise StopIteration

    def siguiente(self) -> Leccion | None:
        return next(self, None)


def vecinas(raiz: NodoContenido, leccion_id: int) -> tuple[int | None, int | None]:
    """Lección anterior y siguiente (sin importar si están completadas)."""
    ids = [l.id for l in raiz.lecciones()]
    i = ids.index(leccion_id)
    return (ids[i - 1] if i > 0 else None, ids[i + 1] if i + 1 < len(ids) else None)
