"""Patrón Observer: cuando un colaborador completa una lección, se avisa a quien
le interese sin que el registro del avance los conozca.

- InvalidadorRuta: borra de la caché la ruta y el árbol de avance del
  colaborador, para que la próxima consulta los recalcule (Cache-Aside).
- Bitacora: deja constancia del avance (auditoría y métricas).
"""
from __future__ import annotations

import threading
import time
from abc import ABC, abstractmethod


class Observador(ABC):
    @abstractmethod
    def notificar(self, evento: str, datos: dict) -> None: ...


class Publicador:
    def __init__(self) -> None:
        self._obs: list[Observador] = []
        self._candado = threading.Lock()

    def suscribir(self, o: Observador) -> None:
        with self._candado:
            self._obs.append(o)

    def publicar(self, evento: str, datos: dict) -> None:
        with self._candado:
            destino = list(self._obs)
        for o in destino:
            o.notificar(evento, datos)


class InvalidadorRuta(Observador):
    def __init__(self, cache) -> None:
        self.cache = cache

    def notificar(self, evento, datos):
        if evento == "leccion.completada":
            self.cache.borrar_prefijo(f"c{datos['colaborador']}:")


class Bitacora(Observador):
    def __init__(self, limite: int = 500) -> None:
        self.eventos: list[dict] = []
        self.limite = limite
        self._candado = threading.Lock()

    def notificar(self, evento, datos):
        with self._candado:
            self.eventos.append({"evento": evento, "momento": time.time(), **datos})
            del self.eventos[:-self.limite]
