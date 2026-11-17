"""Crea la base de datos de demostración (SQLite) con datos ficticios.

Esquema de la iteración 1: solo llaves primarias, como suele quedar la base de
un LMS que creció a punta de plugins. Los índices de la iteración 2 los agrega
el repositorio optimizado (ver repositorio.MIGRACION_V2).

    python -m rutas.datos.semilla --cursos 5000 --colaboradores 2000 --db rutas.db
"""
from __future__ import annotations

import argparse
import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

ESQUEMA = """
CREATE TABLE meta(clave TEXT PRIMARY KEY, valor TEXT);
CREATE TABLE curso(id INTEGER PRIMARY KEY, codigo TEXT UNIQUE, titulo TEXT, categoria TEXT,
                   obligatorio INTEGER, duracion_min INTEGER);
CREATE TABLE prerrequisito(curso_id INTEGER, requiere_id INTEGER, PRIMARY KEY(curso_id, requiere_id));
CREATE TABLE modulo(id INTEGER PRIMARY KEY, curso_id INTEGER, orden INTEGER, titulo TEXT);
CREATE TABLE leccion(id INTEGER PRIMARY KEY, modulo_id INTEGER, curso_id INTEGER, orden INTEGER,
                     titulo TEXT, duracion_min INTEGER);
CREATE TABLE colaborador(id INTEGER PRIMARY KEY, documento TEXT, nombres TEXT, empresa TEXT, cargo TEXT,
                         minutos_dia INTEGER);
CREATE TABLE matricula(colaborador_id INTEGER, curso_id INTEGER, fecha_limite TEXT, motivo TEXT,
                       PRIMARY KEY(colaborador_id, curso_id));
CREATE TABLE avance(colaborador_id INTEGER, leccion_id INTEGER, completada_en TEXT,
                    PRIMARY KEY(colaborador_id, leccion_id));
"""

# Cursos obligatorios: (código, título, categoría, prerrequisitos)
OBLIGATORIOS = [
    ("SST-INDUCCION", "Inducción al SG-SST", "Seguridad y salud en el trabajo", []),
    ("ALTURAS-BASICO", "Trabajo seguro en alturas: nivel básico", "Seguridad y salud en el trabajo", ["SST-INDUCCION"]),
    ("ALTURAS-AVANZADO", "Trabajo seguro en alturas: nivel avanzado", "Seguridad y salud en el trabajo", ["ALTURAS-BASICO"]),
    ("ALTURAS-COORDINADOR", "Coordinador de trabajo en alturas", "Seguridad y salud en el trabajo", ["ALTURAS-AVANZADO"]),
    ("ESPACIOS-CONFINADOS", "Espacios confinados", "Seguridad y salud en el trabajo", ["SST-INDUCCION"]),
    ("RIESGO-ELECTRICO", "Riesgo eléctrico", "Seguridad y salud en el trabajo", ["SST-INDUCCION"]),
    ("PRIMEROS-AUXILIOS", "Primeros auxilios", "Emergencias", []),
    ("BRIGADA", "Brigada de emergencias", "Emergencias", ["PRIMEROS-AUXILIOS"]),
    ("DATOS-1581", "Protección de datos personales (Ley 1581)", "Cumplimiento", []),
    ("BIOSEGURIDAD", "Bioseguridad y manejo de residuos", "Salud", ["SST-INDUCCION"]),
    ("ATENCION-HUMANIZADA", "Atención humanizada en salud", "Salud", []),
    ("SEGURIDAD-PACIENTE", "Seguridad del paciente", "Salud", ["ATENCION-HUMANIZADA"]),
]
RUTAS = {
    "Operario de obra": ["SST-INDUCCION", "ALTURAS-BASICO", "ALTURAS-AVANZADO", "RIESGO-ELECTRICO"],
    "Maestro de obra": ["SST-INDUCCION", "ALTURAS-BASICO", "ALTURAS-AVANZADO", "ALTURAS-COORDINADOR",
                        "ESPACIOS-CONFINADOS", "PRIMEROS-AUXILIOS", "BRIGADA"],
    "Administrativo": ["SST-INDUCCION", "DATOS-1581", "PRIMEROS-AUXILIOS"],
    "Auxiliar de enfermería": ["SST-INDUCCION", "BIOSEGURIDAD", "ATENCION-HUMANIZADA", "SEGURIDAD-PACIENTE", "DATOS-1581"],
    "Médico": ["SST-INDUCCION", "BIOSEGURIDAD", "ATENCION-HUMANIZADA", "SEGURIDAD-PACIENTE", "DATOS-1581",
               "PRIMEROS-AUXILIOS"],
}
CARGOS = {
    "Constructora Los Andes S.A.S.": ["Operario de obra"] * 7 + ["Maestro de obra"] * 2 + ["Administrativo"],
    "Clínica Santa Lucía": ["Auxiliar de enfermería"] * 6 + ["Médico"] * 2 + ["Administrativo"] * 2,
}
TEMAS = {
    "Ofimática": ["Excel", "Word", "PowerPoint", "Tablas dinámicas", "Correo y agenda"],
    "Liderazgo": ["Liderazgo de equipos", "Comunicación asertiva", "Gestión del tiempo", "Retroalimentación"],
    "Calidad": ["ISO 9001", "Indicadores de gestión", "Auditoría interna", "Mejora continua"],
    "Servicio al cliente": ["Atención de quejas", "Servicio telefónico", "Experiencia del cliente"],
    "Finanzas": ["Presupuesto personal", "Costos de obra", "Facturación electrónica"],
    "Tecnología": ["Ciberseguridad básica", "Herramientas colaborativas", "Inteligencia artificial en la oficina"],
    "Salud": ["Manejo del dolor", "Higiene de manos", "Farmacovigilancia"],
    "Seguridad y salud en el trabajo": ["Pausas activas", "Ergonomía", "Orden y aseo"],
}
NIVELES = ["introducción", "nivel 1", "nivel 2", "intermedio", "avanzado", "para supervisores", "casos prácticos"]
NOMBRES = ["Carlos", "Andrés", "Luisa", "María José", "Jhon Fredy", "Yuliana", "Wilson", "Sandra", "Diego",
           "Paola", "Edwin", "Laura", "Jorge Iván", "Natalia", "Brayan", "Angélica", "Óscar", "Diana", "Fabián", "Leidy"]
APELLIDOS = ["Rodríguez", "Gómez", "Rueda", "Pabón", "Duarte", "Ortiz", "Jaimes", "Galvis", "Villamizar",
             "Suárez", "Mantilla", "Ardila", "Quintero", "Prada", "Rincón", "Serrano", "Tarazona"]


def crear(ruta_db: Path, cursos: int = 5000, colaboradores: int = 2000, semilla: int = 2026,
          hoy: date | None = None) -> Path:
    azar = random.Random(semilla)
    hoy = hoy or date(2026, 11, 17)
    ruta_db.unlink(missing_ok=True)
    con = sqlite3.connect(ruta_db)
    con.executescript(ESQUEMA)
    con.execute("INSERT INTO meta VALUES ('hoy', ?)", (hoy.isoformat(),))

    ids: dict[str, int] = {}
    mod_id = lec_id = 0

    def agregar_curso(codigo, titulo, categoria, obligatorio, n_mod, n_lec, dur):
        nonlocal mod_id, lec_id
        cid = len(ids) + 1
        ids[codigo] = cid
        total = 0
        lecciones = []
        for m in range(1, n_mod + 1):
            mod_id += 1
            con.execute("INSERT INTO modulo VALUES (?,?,?,?)", (mod_id, cid, m, f"Módulo {m}"))
            for k in range(1, n_lec + 1):
                lec_id += 1
                d = azar.randint(*dur)
                total += d
                lecciones.append((lec_id, mod_id, cid, k, f"Lección {m}.{k}", d))
        con.executemany("INSERT INTO leccion VALUES (?,?,?,?,?,?)", lecciones)
        con.execute("INSERT INTO curso VALUES (?,?,?,?,?,?)", (cid, codigo, titulo, categoria, obligatorio, total))

    for codigo, titulo, cat, _ in OBLIGATORIOS:
        agregar_curso(codigo, titulo, cat, 1, azar.randint(3, 4), azar.randint(3, 5), (8, 16))
    for codigo, _, _, reqs in OBLIGATORIOS:
        con.executemany("INSERT INTO prerrequisito VALUES (?,?)", [(ids[codigo], ids[r]) for r in reqs])
    cats = list(TEMAS)
    for n in range(1, cursos - len(OBLIGATORIOS) + 1):
        cat = cats[n % len(cats)]
        tema = azar.choice(TEMAS[cat])
        agregar_curso(f"EL-{n:05d}", f"{tema}: {azar.choice(NIVELES)} ({n:05d})", cat, 0,
                      azar.randint(2, 4), azar.randint(2, 4), (5, 15))

    lecciones_de = {}
    for cid, lid in con.execute("SELECT curso_id, id FROM leccion WHERE curso_id <= ?", (len(OBLIGATORIOS),)):
        lecciones_de.setdefault(cid, []).append(lid)

    for i in range(1, colaboradores + 1):
        empresa = "Constructora Los Andes S.A.S." if i % 2 else "Clínica Santa Lucía"
        cargo = azar.choice(CARGOS[empresa])
        nombre = f"{azar.choice(NOMBRES)} {azar.choice(APELLIDOS)} {azar.choice(APELLIDOS)}"
        con.execute("INSERT INTO colaborador VALUES (?,?,?,?,?,?)",
                    (i, str(1_095_000_000 + i), nombre, empresa, cargo, azar.choice([15, 20, 30, 30, 45])))
        cierre = hoy + timedelta(days=azar.randint(10, 35))  # cierre de la campaña de la empresa
        for codigo in RUTAS[cargo]:
            cid = ids[codigo]
            r = azar.random()
            if r < 0.25:  # ya lo tenía: certificado vigente, se marca todo como completado
                con.executemany("INSERT INTO avance VALUES (?,?,?)",
                                [(i, l, (hoy - timedelta(days=60)).isoformat()) for l in lecciones_de[cid]])
                continue
            if codigo == "ALTURAS-AVANZADO" and azar.random() < 0.5:
                limite, motivo = hoy + timedelta(days=azar.randint(5, 25)), "vencimiento"  # reentrenamiento
            else:
                limite, motivo = cierre, "campaña"
            con.execute("INSERT INTO matricula VALUES (?,?,?,?)", (i, cid, limite.isoformat(), motivo))
            if r < 0.45:  # avance parcial
                hechas = lecciones_de[cid][: azar.randint(1, len(lecciones_de[cid]) - 1)]
                con.executemany("INSERT INTO avance VALUES (?,?,?)",
                                [(i, l, (hoy - timedelta(days=3)).isoformat()) for l in hechas])
        # Algunos cursos electivos, sin fecha límite
        for cid in azar.sample(range(len(OBLIGATORIOS) + 1, len(ids) + 1), azar.randint(1, 3)):
            con.execute("INSERT INTO matricula VALUES (?,?,?,?)",
                        (i, cid, (hoy + timedelta(days=365)).isoformat(), "voluntario"))
    con.commit()
    con.close()
    return ruta_db


def main() -> None:
    p = argparse.ArgumentParser(description="Crea la base de demostración de AulaNube Rutas")
    p.add_argument("--db", default="rutas.db")
    p.add_argument("--cursos", type=int, default=5000)
    p.add_argument("--colaboradores", type=int, default=2000)
    a = p.parse_args()
    ruta = crear(Path(a.db), a.cursos, a.colaboradores)
    con = sqlite3.connect(ruta)
    print({t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
           for t in ("curso", "modulo", "leccion", "colaborador", "matricula", "avance")})


if __name__ == "__main__":
    main()
