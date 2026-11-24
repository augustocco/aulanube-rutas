"""Gráficos del informe a partir de docs/resultados/resultados.json."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
R = json.loads((RAIZ / "docs" / "resultados" / "resultados.json").read_text(encoding="utf-8"))
SAL = RAIZ / "docs" / "resultados"

# Paleta validada en la Unidad 2 (verde azulado y naranja) más un gris neutro para la línea base.
V1, V2, V3 = "#9aa5a8", "#c2410c", "#00897b"
TINTA, TINTA_2, REJILLA, FONDO = "#16323a", "#5b6b70", "#e6e3da", "#ffffff"
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": REJILLA, "axes.labelcolor": TINTA_2,
    "xtick.color": TINTA_2, "ytick.color": TINTA_2, "axes.titlesize": 11, "axes.titleweight": "bold",
    "axes.titlecolor": TINTA, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
    "axes.grid.axis": "y", "grid.color": REJILLA, "grid.linewidth": 0.8, "figure.facecolor": FONDO,
    "axes.facecolor": FONDO, "savefig.dpi": 200,
})


def num(x, d=1):
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def etiqueta(ax, x, y, texto):
    ax.annotate(texto, (x, y), xytext=(0, 4), textcoords="offset points", ha="center", va="bottom",
                fontsize=9, color=TINTA, bbox=dict(boxstyle="square,pad=0.1", fc=FONDO, ec="none"))


def ruta() -> None:
    e = R["E1"]
    nombres = {"alfabetico": "Alfabético\n(actual)", "fecha": "Primero lo\nque vence", "urgencia": "Urgencia con\nprerrequisitos"}
    colores = [V1, V2, V3]
    fig, (a, b) = plt.subplots(1, 2, figsize=(10, 3.6))
    for ax, clave, titulo in ((a, "a_tiempo_pct", "Cursos obligatorios a tiempo"),
                              (b, "vencimientos_con_prerrequisito_a_tiempo_pct",
                               "Reentrenamientos con prerrequisito pendiente")):
        ys = [e[k][clave] for k in nombres]
        ax.bar(range(3), ys, color=colores, width=0.6, edgecolor=FONDO, linewidth=1.5, zorder=3)
        for i, y in enumerate(ys):
            etiqueta(ax, i, y, f"{num(y)} %")
        ax.set_xticks(range(3), list(nombres.values()))
        ax.set_ylim(0, 100)
        ax.set_title(titulo, loc="left")
    a.set_ylabel("Porcentaje a tiempo")
    fig.tight_layout()
    fig.savefig(SAL / "fig-ruta.png")
    plt.close(fig)


def carga() -> None:
    e = R["E2"]
    niveles = [int(n) for n in e["v1"]]
    fig, (a, b) = plt.subplots(1, 2, figsize=(10, 3.7))
    for v, color, nombre in (("v1", V1, "Iteración 1"), ("v2", V2, "Iteración 2"), ("v3", V3, "Iteración 3")):
        a.plot(niveles, [e[v][str(n)]["rps"] for n in niveles], marker="o", lw=2, ms=6, color=color, label=nombre)
        b.plot(niveles, [e[v][str(n)]["por_tipo"]["completar"]["p95_ms"] / 1000 for n in niveles], marker="o",
               lw=2, ms=6, color=color, label=nombre)
    a.set_title("Solicitudes atendidas por segundo", loc="left")
    a.set_xlabel("Usuarios concurrentes")
    b.set_title("p95 de «completar lección» (s, escala log)", loc="left")
    b.set_yscale("log")
    from matplotlib.ticker import FuncFormatter
    b.yaxis.set_major_formatter(FuncFormatter(lambda v, _: num(v, max(0, -int(f"{v:e}".split("e")[1])))))
    b.set_xlabel("Usuarios concurrentes")
    for ax in (a, b):
        ax.set_xticks(niveles)
    a.legend(frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(SAL / "fig-carga.png")
    plt.close(fig)


def catalogo() -> None:
    e = R["E3"]
    pags = [int(p) for p in e["v1"]]
    fig, ax = plt.subplots(figsize=(7.2, 3.3))
    ax.plot(pags, [e["v1"][str(p)] for p in pags], marker="o", lw=2, color=V2, label="OFFSET (iteración 1)")
    ax.plot(pags, [e["v2"][str(p)] for p in pags], marker="o", lw=2, color=V3, label="Keyset + índice (iteración 2)")
    ax.annotate(f"{num(e['v1'][str(pags[-1])])} ms", (pags[-1], e["v1"][str(pags[-1])]), xytext=(-6, 4),
                textcoords="offset points", ha="right", fontsize=9, color=TINTA)
    ax.annotate(f"{num(e['v2'][str(pags[-1])], 2)} ms", (pags[-1], e["v2"][str(pags[-1])]), xytext=(-6, 6),
                textcoords="offset points", ha="right", fontsize=9, color=TINTA)
    ax.set_xlabel("Número de página (20 cursos por página, catálogo de 50.000)")
    ax.set_ylabel("Mediana (ms)")
    ax.set_title("Costo de ir a la página N del catálogo", loc="left")
    ax.legend(frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(SAL / "fig-catalogo.png")
    plt.close(fig)


if __name__ == "__main__":
    ruta()
    carga()
    catalogo()
    print("Gráficos en", SAL)


# ---------------------------------------------------------------- versiones simples para la presentación
def ppt_ruta() -> None:
    """De cada 100 cursos obligatorios, ¿cuántos terminan a tiempo?"""
    e = R["E1"]
    filas = [("Orden alfabético (hoy)", e["alfabetico"]["a_tiempo_pct"], V1),
             ("Primero lo que vence", e["fecha"]["a_tiempo_pct"], V2),
             ("Urgencia con prerrequisitos", e["urgencia"]["a_tiempo_pct"], V3)]
    fig, ax = plt.subplots(figsize=(5.0, 2.3))
    for i, (nombre, v, color) in enumerate(reversed(filas)):
        ax.barh(i, v, color=color, height=0.6, zorder=3)
        ax.text(v + 1.5, i, f"{round(v)} de cada 100", va="center", fontsize=12, color=TINTA, fontweight="bold")
    ax.set_yticks(range(3), [f[0] for f in reversed(filas)], fontsize=11)
    ax.set_xlim(0, 165)
    ax.set_xticks([])
    ax.grid(False)
    ax.spines[["left", "bottom"]].set_visible(False)
    ax.tick_params(axis="y", length=0)
    fig.tight_layout()
    fig.savefig(SAL / "ppt-ruta.png")
    plt.close(fig)


def ppt_carga() -> None:
    """Con 50 personas a la vez: ¿cuántas solicitudes atiende por segundo cada iteración?"""
    e = R["E2"]
    mx = str(max(int(k) for k in e["v1"]))
    filas = [("Iteración 1\n(hoy)", e["v1"][mx]["rps"], V1), ("Iteración 2\n(lecturas)", e["v2"][mx]["rps"], V2),
             ("Iteración 3\n(+ cola)", e["v3"][mx]["rps"], V3)]
    fig, ax = plt.subplots(figsize=(4.6, 3.0))
    for i, (nombre, v, color) in enumerate(filas):
        ax.bar(i, v, color=color, width=0.6, zorder=3)
        ax.text(i, v + 20, f"{round(v):,}".replace(",", "."), ha="center", va="bottom", fontsize=14,
                fontweight="bold", color=TINTA)
    ax.set_xticks(range(3), [f[0] for f in filas], fontsize=11)
    ax.set_ylim(0, max(f[1] for f in filas) * 1.2)
    ax.set_yticks([])
    ax.grid(False)
    ax.spines[["left"]].set_visible(False)
    ax.set_title("Solicitudes atendidas por segundo", loc="left", fontsize=12)
    fig.tight_layout()
    fig.savefig(SAL / "ppt-carga.png")
    plt.close(fig)


ppt_ruta()
ppt_carga()


def ppt_catalogo() -> None:
    """Tiempo para mostrar la página 1 y la página más profunda, hoy y con el marcapáginas."""
    e = R["E3"]
    pm = str(max(int(k) for k in e["v1"]))
    grupos = [("Página 1", "1"), (f"Página {int(pm):,}".replace(",", "."), pm)]
    fig, ax = plt.subplots(figsize=(4.6, 3.0))
    ancho = 0.36
    for g, (nombre, k) in enumerate(grupos):
        for d, (v, color, etq) in enumerate(((e["v1"][k], V2, "Hoy"), (e["v2"][k], V3, "Nueva"))):
            x = g + (d - 0.5) * (ancho + 0.04)
            ax.bar(x, v, width=ancho, color=color, zorder=3)
            texto = f"{num(v, 0)} ms" if v >= 1 else f"{num(v, 2)} ms"
            ax.text(x, v + 3, texto, ha="center", va="bottom", fontsize=12, fontweight="bold", color=TINTA)
    ax.set_xticks(range(2), [g[0] for g in grupos], fontsize=12)
    ax.set_ylim(0, e["v1"][pm] * 1.25)
    ax.set_yticks([])
    ax.grid(False)
    ax.spines[["left"]].set_visible(False)
    ax.set_title("Tiempo para mostrar una página", loc="left", fontsize=12)
    ax.legend(handles=[Patch(color=V2, label="Hoy (contando)"), Patch(color=V3, label="Nueva (marcapáginas)")],
              frameon=False, fontsize=10, loc="upper left")
    fig.tight_layout()
    fig.savefig(SAL / "ppt-catalogo.png")
    plt.close(fig)


ppt_catalogo()
