"""Actualiza la tabla de contenido del informe en Word y cuenta las páginas.

Con --revisar <carpeta> exporta además una copia en PDF a esa carpeta, solo para revisión visual
(la entrega es en Word y PowerPoint).
"""
from __future__ import annotations

import sys
from pathlib import Path

import win32com.client as win32

RAIZ = Path(__file__).resolve().parent.parent
INFORME = RAIZ / "docs" / "informe" / "Informe-AulaNube-Rutas.docx"
PRESENTACION = RAIZ / "docs" / "presentacion" / "Presentacion-AulaNube-Rutas.pptx"
revisar = Path(sys.argv[sys.argv.index("--revisar") + 1]) if "--revisar" in sys.argv else None

word = win32.DispatchEx("Word.Application")
word.Visible = False
word.DisplayAlerts = 0
try:
    d = word.Documents.Open(str(INFORME))
    d.Fields.Update()
    for toc in d.TablesOfContents:
        toc.Update()
    d.Save()
    print("páginas del informe:", d.ComputeStatistics(2))
    if revisar:
        d.ExportAsFixedFormat(str(revisar / "informe-revision.pdf"), 17)
    d.Close(False)
finally:
    word.Quit()

if revisar and PRESENTACION.exists():
    ppt = win32.DispatchEx("PowerPoint.Application")
    try:
        p = ppt.Presentations.Open(str(PRESENTACION), WithWindow=False)
        p.SaveAs(str(revisar / "presentacion-revision.pdf"), 32)
        p.Close()
    finally:
        ppt.Quit()
