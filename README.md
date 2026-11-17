# AulaNube Rutas

Prototipo de la actividad 6 **«Navegando mareas: Estrategias de navegación en la arquitectura de software»** (Arquitectura de Software, Unidad 3, Tecnológica del Oriente).

Cierra el caso de AulaNube (Unidad 1: [aulanube](https://github.com/augustocco/aulanube); Unidad 2: [aulanube-malla](https://github.com/augustocco/aulanube-malla)). Tras el cargue de RRHH, el colaborador ya está matriculado; este servicio le arma una **ruta de formación por urgencia** (prerrequisitos, cierre de campaña y vencimiento de certificados) y lo lleva con **«Continuar»** a su siguiente lección pendiente. Se evalúa en tres iteraciones:

| Iteración | Qué cambia |
|---|---|
| v1 | Lo de hoy: lista alfabética, consultas lección por lección (N+1), catálogo con OFFSET |
| v2 | Ruta por urgencia, consultas agrupadas, índices, caché a un lado y paginación por llave |
| v3 | v2 + el avance va a una cola y un hilo lo guarda por lotes cada 100 ms |

Patrones: Strategy (ruta), Composite + Iterator (contenido), Command (navegación y «Atrás»), Observer (invalidación de caché), Cache-Aside, Repository y cola de escritura.

## En la nube

Desplegado en el clúster K3s de la Unidad 1 (Oracle Cloud, sa-bogota-1), espacio de nombres `aulanube-rutas`:

- Iteración 3: https://rutas.149-130-191-139.sslip.io
- Iteración 1: https://rutas-v1.149-130-191-139.sslip.io

Para volver a desplegar: `bash scripts/desplegar.sh` (requiere que la lista de seguridad de OCI permita SSH desde la IP pública actual).

## Ejecución

Python 3.11 o superior, sin dependencias.

```bash
python -m rutas.servidor --version v3 --db rutas.db --puerto 7400   # crea la base de demostración la primera vez
```

Abra http://127.0.0.1:7400. Para comparar, levante otra instancia con `--version v1` en otro puerto y otra copia de la base.

## Pruebas y evaluación

```bash
python -m unittest discover -s tests -t .   # 14 pruebas: dominio y equivalencia v1 = v2 = v3
python scripts/evaluar.py                    # E1 ruta, E2 carga (1-50 usuarios), E3 catálogo de 50.000 cursos
python scripts/graficar.py
python scripts/construir_informe.py <enlace-video>
python scripts/construir_presentacion.py <enlace-video>
python scripts/actualizar_word.py            # actualiza la tabla de contenido del informe (Windows + Word)
```

## Estructura

```
rutas/dominio/      contenido.py (Composite, Iterator) · ruta.py (Strategy) · eventos.py (Observer)
rutas/datos/        semilla.py (datos ficticios) · repositorio.py (v1, v2, v3 y caché)
rutas/servicio.py   ServicioNavegacion (sin estado)
rutas/servidor.py   API HTTP
rutas/vista/        index.html (Mi ruta, lector, catálogo; Command en JavaScript)
docs/uml            componentes, clases, secuencia y actividad (PlantUML)
docs/resultados     resultados.json y gráficos
docs/informe        informe en Word · docs/presentacion: PowerPoint, guion, miniatura
```
