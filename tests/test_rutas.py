"""Pruebas de AulaNube Rutas: dominio, estrategias y equivalencia v1 = v2."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from rutas.datos.repositorio import Cache, RepositorioIngenuo, RepositorioOptimizado
from rutas.datos.semilla import crear
from rutas.dominio.contenido import Curso, IteradorPendientes, Leccion, Modulo, vecinas
from rutas.dominio.eventos import InvalidadorRuta, Publicador
from rutas.dominio.ruta import CursoPendiente, OrdenAlfabetico, PorFechaLimite, PorUrgencia, planificar
from rutas.servicio import ServicioNavegacion


def curso_ejemplo() -> Curso:
    k = Curso(1, "Alturas")
    for m in (1, 2):
        mod = Modulo(m, f"Módulo {m}")
        for l in (1, 2):
            mod.agregar(Leccion(m * 10 + l, f"Lección {m}.{l}", 10))
        k.agregar(mod)
    return k


class ContenidoPruebas(unittest.TestCase):
    def test_composite_suma_minutos_de_hojas(self):
        k = curso_ejemplo()
        self.assertEqual(k.minutos_totales(), 40)
        self.assertEqual(k.minutos_pendientes({11, 12}), 20)
        self.assertEqual(k.hijos[0].minutos_totales(), 20)

    def test_iterador_salta_lo_completado(self):
        k = curso_ejemplo()
        it = IteradorPendientes(k, completadas={11, 12, 21})
        self.assertEqual(it.siguiente().id, 22)
        self.assertIsNone(it.siguiente())

    def test_iterador_desde_una_posicion(self):
        self.assertEqual([l.id for l in IteradorPendientes(curso_ejemplo(), {12}, desde=12)], [21, 22])

    def test_vecinas(self):
        self.assertEqual(vecinas(curso_ejemplo(), 12), (11, 21))


def c(codigo, minutos, vence, reqs=(), motivo="campaña"):
    return CursoPendiente(codigo, codigo, minutos, vence, motivo, frozenset(reqs))


class EstrategiasPruebas(unittest.TestCase):
    # Basico (campaña, día 20) es prerrequisito de Avanzado, cuyo certificado vence el día 8.
    # Riesgo (campaña, día 15) no tiene relación con ellos, pero vence antes que Básico.
    CURSOS = [c("BASICO", 120, 20), c("AVANZADO", 120, 8, ["BASICO"], "vencimiento"), c("RIESGO", 120, 15)]

    def test_urgencia_hereda_la_fecha_del_curso_que_depende(self):
        plan = planificar(self.CURSOS, PorUrgencia(), minutos_dia=30)
        self.assertEqual([i.codigo for i in plan], ["BASICO", "AVANZADO", "RIESGO"])
        self.assertTrue(next(i for i in plan if i.codigo == "AVANZADO").a_tiempo)

    def test_fecha_simple_no_ve_la_dependencia(self):
        plan = planificar(self.CURSOS, PorFechaLimite(), minutos_dia=30)
        self.assertFalse(next(i for i in plan if i.codigo == "AVANZADO").a_tiempo)

    def test_alfabetico_marca_lo_bloqueado(self):
        plan = planificar(self.CURSOS, OrdenAlfabetico(), minutos_dia=30)
        self.assertEqual(plan[0].codigo, "AVANZADO")
        self.assertEqual(plan[0].bloqueado_por, ["BASICO"])

    def test_ciclo_de_prerrequisitos_se_detecta(self):
        with self.assertRaises(ValueError):
            PorUrgencia().preferencia([c("A", 10, 5, ["B"]), c("B", 10, 5, ["A"])], 30)


class ObservadorPruebas(unittest.TestCase):
    def test_completar_invalida_solo_la_ruta_del_colaborador(self):
        cache, pub = Cache(), Publicador()
        pub.suscribir(InvalidadorRuta(cache))
        cache.obtener("c7:ruta:urgencia", lambda: "plan 7")
        cache.obtener("c8:ruta:urgencia", lambda: "plan 8")
        pub.publicar("leccion.completada", {"colaborador": 7, "leccion": 1})
        self.assertEqual(cache.obtener("c7:ruta:urgencia", lambda: "nuevo"), "nuevo")
        self.assertEqual(cache.obtener("c8:ruta:urgencia", lambda: "nuevo"), "plan 8")


class EquivalenciaPruebas(unittest.TestCase):
    """La iteración 2 debe responder exactamente lo mismo que la 1, solo que más rápido."""

    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.TemporaryDirectory()
        base = Path(cls.dir.name) / "base.db"
        crear(base, cursos=400, colaboradores=60)
        cls.v1 = RepositorioIngenuo(str(base))
        copia = Path(cls.dir.name) / "v2.db"
        copia.write_bytes(base.read_bytes())
        cls.v2 = RepositorioOptimizado(str(copia), Cache())
        cls.ruta_v2 = str(copia)

    @classmethod
    def tearDownClass(cls):
        for r in (cls.v1, cls.v2):
            r.con().close()
        cls.dir.cleanup()

    def test_mismos_pendientes(self):
        for cid in range(1, 60):  # el 60 lo modifica la prueba de completar
            a = sorted(self.v1.pendientes(cid), key=lambda x: x.codigo)
            b = sorted(self.v2.pendientes(cid), key=lambda x: x.codigo)
            self.assertEqual(a, b, f"colaborador {cid}")

    def test_misma_pagina_con_offset_y_keyset(self):
        cursor, pagina = "", 1
        while True:
            a, b = self.v1.catalogo(pagina=pagina), self.v2.catalogo(despues=cursor)
            self.assertEqual([x["id"] for x in a["cursos"]], [x["id"] for x in b["cursos"]])
            if not b["siguiente"]:
                break
            cursor, pagina = b["siguiente"], pagina + 1
        self.assertEqual(pagina, 20)

    def test_mismo_arbol_y_menos_consultas(self):
        self.v1.reiniciar_conteo()
        a = self.v1.arbol(3)
        q1 = self.v1.consultas
        self.v2.reiniciar_conteo()
        b = self.v2.arbol(3)
        self.assertEqual([l.id for l in a.lecciones()], [l.id for l in b.lecciones()])
        self.assertLess(self.v2.consultas, q1)

    def test_continuar_y_completar(self):
        s = ServicioNavegacion(self.ruta_v2, "v2")
        d = s.continuar(60)
        if d.get("terminado"):
            self.skipTest("el colaborador no tiene pendientes")
        r = s.completar(60, d["leccion"]["id"])
        self.assertTrue(r["leccion"]["completada"])
        self.assertNotEqual(s.continuar(60)["leccion"]["id"], d["leccion"]["id"])
        s.repo.con().close()


class EscrituraPorLotesPruebas(unittest.TestCase):
    """v3: el avance sale de la cola hacia la base, y mientras tanto el colaborador ya lo ve."""

    def test_leer_lo_que_uno_mismo_escribio_y_persistencia(self):
        import time
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
            base = Path(d) / "v3.db"
            crear(base, cursos=300, colaboradores=20)
            s = ServicioNavegacion(str(base), "v3")
            antes = {p.codigo: p.minutos_pendientes for p in s.repo.pendientes(3)}
            leccion = s.continuar(3)
            if leccion.get("terminado"):
                self.skipTest("sin pendientes")
            lid = leccion["leccion"]["id"]
            r = s.completar(3, lid)                       # responde antes de escribir en la base
            self.assertTrue(r["leccion"]["completada"])
            despues = {p.codigo: p.minutos_pendientes for p in s.repo.pendientes(3)}
            self.assertLess(sum(despues.values()), sum(antes.values()))
            time.sleep(0.5)                                # el escritor guarda el lote
            fila = s.repo.con().execute("SELECT 1 FROM avance WHERE colaborador_id=3 AND leccion_id=?", (lid,)).fetchone()
            self.assertIsNotNone(fila)
            self.assertEqual({p.codigo: p.minutos_pendientes for p in s.repo.pendientes(3)}, despues)
            s.repo.con().close()


if __name__ == "__main__":
    unittest.main()
