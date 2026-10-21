"""Genera los documentos Word (.docx) de la carpeta docs/ a partir de los Markdown.

Uso:  uv run python scripts/generar_word.py

- docs/guia-tecnica.md        -> docs/word/Guia-tecnica.docx
- docs/sesiones/NN-nombre.md  -> docs/word/Sesion-NN-nombre.docx  (uno por sesión)

Los Word llevan el logo y los colores de Transportes Hidalgo (tomados de `flota.marca`).
Requiere pandoc instalado: https://pandoc.org
"""

from __future__ import annotations

import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DOCS = RAIZ / "docs"
SALIDA = DOCS / "word"
FILTRO_LUA = Path(__file__).with_name("word_filtro.lua")

sys.path.insert(0, str(RAIZ / "src"))
from flota import marca  # noqa: E402  (necesita el sys.path de arriba)


def color(nombre: str) -> str:
    """Color de la marca sin '#', como lo espera Word."""
    return marca.color_excel(nombre)


# Ancho útil de una hoja A4 con márgenes de 2 cm, en DXA (1 cm = 567 DXA).
ANCHO_UTIL = 11906 - 2 * 1134

# ---------- Estilos de Word (XML de word/styles.xml) ----------
# Cada entrada reemplaza el estilo de igual id en la plantilla de pandoc (o se agrega si no existe).
ESTILOS: dict[str, str] = {
    "Normal": f"""
<w:style w:type="paragraph" w:default="1" w:styleId="Normal">
  <w:name w:val="Normal"/><w:qFormat/>
  <w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:cs="Calibri"/>
    <w:color w:val="{color("texto")}"/><w:sz w:val="22"/><w:szCs w:val="22"/></w:rPr>
</w:style>""",
    "BodyText": """
<w:style w:type="paragraph" w:styleId="BodyText">
  <w:name w:val="Body Text"/><w:basedOn w:val="Normal"/><w:link w:val="BodyTextChar"/><w:qFormat/>
  <w:pPr><w:spacing w:before="60" w:after="120" w:line="276" w:lineRule="auto"/></w:pPr>
</w:style>""",
    "Compact": """
<w:style w:type="paragraph" w:customStyle="1" w:styleId="Compact">
  <w:name w:val="Compact"/><w:basedOn w:val="BodyText"/><w:qFormat/>
  <w:pPr><w:spacing w:before="20" w:after="20"/></w:pPr>
</w:style>""",
    "Title": f"""
<w:style w:type="paragraph" w:styleId="Title">
  <w:name w:val="Title"/><w:basedOn w:val="Normal"/><w:next w:val="Subtitle"/><w:qFormat/>
  <w:pPr><w:spacing w:before="240" w:after="60"/></w:pPr>
  <w:rPr><w:b/><w:color w:val="{color("azul-oscuro")}"/><w:sz w:val="48"/><w:szCs w:val="48"/></w:rPr>
</w:style>""",
    "Subtitle": f"""
<w:style w:type="paragraph" w:styleId="Subtitle">
  <w:name w:val="Subtitle"/><w:basedOn w:val="Normal"/><w:next w:val="BodyText"/><w:qFormat/>
  <w:pPr><w:pBdr><w:bottom w:val="single" w:sz="18" w:space="8" w:color="{color("naranja")}"/></w:pBdr>
    <w:spacing w:after="360"/></w:pPr>
  <w:rPr><w:color w:val="{color("naranja-oscuro")}"/><w:sz w:val="26"/><w:szCs w:val="26"/></w:rPr>
</w:style>""",
    "Heading1": f"""
<w:style w:type="paragraph" w:styleId="Heading1">
  <w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:next w:val="BodyText"/>
  <w:uiPriority w:val="9"/><w:qFormat/>
  <w:pPr><w:keepNext/><w:keepLines/>
    <w:pBdr><w:bottom w:val="single" w:sz="8" w:space="4" w:color="{color("naranja")}"/></w:pBdr>
    <w:spacing w:before="480" w:after="160"/><w:outlineLvl w:val="0"/></w:pPr>
  <w:rPr><w:b/><w:color w:val="{color("azul")}"/><w:sz w:val="32"/><w:szCs w:val="32"/></w:rPr>
</w:style>""",
    "Heading2": f"""
<w:style w:type="paragraph" w:styleId="Heading2">
  <w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:next w:val="BodyText"/>
  <w:uiPriority w:val="9"/><w:unhideWhenUsed/><w:qFormat/>
  <w:pPr><w:keepNext/><w:keepLines/><w:spacing w:before="320" w:after="100"/>
    <w:outlineLvl w:val="1"/></w:pPr>
  <w:rPr><w:b/><w:color w:val="{color("azul-oscuro")}"/><w:sz w:val="26"/><w:szCs w:val="26"/></w:rPr>
</w:style>""",
    "Heading3": f"""
<w:style w:type="paragraph" w:styleId="Heading3">
  <w:name w:val="heading 3"/><w:basedOn w:val="Normal"/><w:next w:val="BodyText"/>
  <w:uiPriority w:val="9"/><w:unhideWhenUsed/><w:qFormat/>
  <w:pPr><w:keepNext/><w:keepLines/><w:spacing w:before="240" w:after="80"/>
    <w:outlineLvl w:val="2"/></w:pPr>
  <w:rPr><w:b/><w:color w:val="{color("naranja-oscuro")}"/><w:sz w:val="23"/><w:szCs w:val="23"/></w:rPr>
</w:style>""",
    "BlockText": f"""
<w:style w:type="paragraph" w:styleId="BlockText">
  <w:name w:val="Block Text"/><w:basedOn w:val="BodyText"/><w:next w:val="BodyText"/><w:qFormat/>
  <w:pPr><w:pBdr><w:left w:val="single" w:sz="24" w:space="8" w:color="{color("naranja")}"/></w:pBdr>
    <w:shd w:val="clear" w:color="auto" w:fill="{color("naranja-claro")}"/>
    <w:spacing w:before="120" w:after="120"/><w:ind w:left="240" w:right="240"/></w:pPr>
</w:style>""",
    "SourceCode": f"""
<w:style w:type="paragraph" w:customStyle="1" w:styleId="SourceCode">
  <w:name w:val="Source Code"/><w:basedOn w:val="Normal"/><w:link w:val="VerbatimChar"/>
  <w:pPr>
    <w:pBdr><w:left w:val="single" w:sz="18" w:space="6" w:color="{color("azul")}"/></w:pBdr>
    <w:shd w:val="clear" w:color="auto" w:fill="{color("fondo")}"/>
    <w:wordWrap w:val="off"/>
    <w:spacing w:before="120" w:after="160" w:line="240" w:lineRule="auto"/><w:ind w:left="160"/></w:pPr>
  <w:rPr><w:rFonts w:ascii="Consolas" w:hAnsi="Consolas"/><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr>
</w:style>""",
    "VerbatimChar": f"""
<w:style w:type="character" w:customStyle="1" w:styleId="VerbatimChar">
  <w:name w:val="Verbatim Char"/><w:basedOn w:val="DefaultParagraphFont"/>
  <w:rPr><w:rFonts w:ascii="Consolas" w:hAnsi="Consolas"/><w:color w:val="{color("azul-oscuro")}"/>
    <w:sz w:val="19"/><w:szCs w:val="19"/><w:shd w:val="clear" w:color="auto" w:fill="{color("fondo")}"/></w:rPr>
</w:style>""",
    "Hyperlink": f"""
<w:style w:type="character" w:styleId="Hyperlink">
  <w:name w:val="Hyperlink"/><w:basedOn w:val="DefaultParagraphFont"/>
  <w:rPr><w:color w:val="{color("azul")}"/><w:u w:val="single"/></w:rPr>
</w:style>""",
    "Table": f"""
<w:style w:type="table" w:default="1" w:styleId="Table">
  <w:name w:val="Table"/><w:basedOn w:val="TableNormal"/><w:qFormat/>
  <w:tblPr>
    <w:tblBorders>
      <w:top w:val="single" w:sz="4" w:space="0" w:color="{color("borde")}"/>
      <w:left w:val="single" w:sz="4" w:space="0" w:color="{color("borde")}"/>
      <w:bottom w:val="single" w:sz="4" w:space="0" w:color="{color("borde")}"/>
      <w:right w:val="single" w:sz="4" w:space="0" w:color="{color("borde")}"/>
      <w:insideH w:val="single" w:sz="4" w:space="0" w:color="{color("borde")}"/>
      <w:insideV w:val="single" w:sz="4" w:space="0" w:color="{color("borde")}"/>
    </w:tblBorders>
    <w:tblCellMar><w:top w:w="40" w:type="dxa"/><w:left w:w="100" w:type="dxa"/>
      <w:bottom w:w="40" w:type="dxa"/><w:right w:w="100" w:type="dxa"/></w:tblCellMar>
  </w:tblPr>
  <w:tblStylePr w:type="firstRow">
    <w:rPr><w:b/><w:color w:val="{color("azul-oscuro")}"/></w:rPr>
    <w:tcPr><w:shd w:val="clear" w:color="auto" w:fill="{color("azul-claro")}"/></w:tcPr>
  </w:tblStylePr>
</w:style>""",
}

PIE_DE_PAGINA = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:ftr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
       xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <w:p>
    <w:pPr>
      <w:pBdr><w:top w:val="single" w:sz="6" w:space="4" w:color="{color("naranja")}"/></w:pBdr>
      <w:tabs><w:tab w:val="right" w:pos="{ANCHO_UTIL}"/></w:tabs>
      <w:spacing w:after="0"/>
      <w:rPr><w:color w:val="{color("texto-suave")}"/><w:sz w:val="18"/></w:rPr>
    </w:pPr>
    {{runs}}
  </w:p>
</w:ftr>"""


def _run(contenido: str) -> str:
    return (
        f'<w:r><w:rPr><w:color w:val="{color("texto-suave")}"/><w:sz w:val="18"/></w:rPr>'
        f"{contenido}</w:r>"
    )


def _campo(instruccion: str) -> str:
    """Campo de Word que se calcula al abrir (número de página, total de páginas)."""
    return (
        _run('<w:fldChar w:fldCharType="begin"/>')
        + _run(f'<w:instrText xml:space="preserve"> {instruccion} </w:instrText>')
        + _run('<w:fldChar w:fldCharType="separate"/>')
        + _run("<w:t>1</w:t>")
        + _run('<w:fldChar w:fldCharType="end"/>')
    )


def _pie_de_pagina() -> str:
    runs = (
        _run(f'<w:t xml:space="preserve">{marca.NOMBRE_EMPRESA} · Gestión de Flota</w:t>')
        + _run('<w:tab/><w:t xml:space="preserve">Página </w:t>')
        + _campo("PAGE")
        + _run('<w:t xml:space="preserve"> de </w:t>')
        + _campo("NUMPAGES")
    )
    return PIE_DE_PAGINA.replace("{runs}", runs)


SECCION = """<w:sectPr>
      <w:footerReference w:type="default" r:id="rIdPieHidalgo"/>
      <w:footnotePr><w:numRestart w:val="eachSect"/></w:footnotePr>
      <w:pgSz w:w="11906" w:h="16838"/>
      <w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134"
               w:header="567" w:footer="567" w:gutter="0"/>
    </w:sectPr>"""


def _reemplazar_estilos(xml: str) -> str:
    # Idioma español (Argentina) para la corrección ortográfica de Word.
    xml = re.sub(r"<w:lang [^>]*/>", '<w:lang w:val="es-AR" w:eastAsia="es-AR"/>', xml)
    for id_estilo, nuevo in ESTILOS.items():
        patron = re.compile(rf'<w:style\b[^>]*\bw:styleId="{id_estilo}"[^>]*>.*?</w:style>', re.S)
        xml, cambios = patron.subn(lambda _, n=nuevo: n.strip(), xml)
        if not cambios:
            xml = xml.replace("</w:styles>", nuevo.strip() + "\n</w:styles>")
    return xml


def crear_plantilla(destino: Path) -> None:
    """Toma la plantilla de pandoc y le aplica estilos, márgenes y pie de página de la marca."""
    base = subprocess.run(
        ["pandoc", "--print-default-data-file", "reference.docx"], capture_output=True, check=True
    ).stdout
    with (
        zipfile.ZipFile(io.BytesIO(base)) as origen,
        zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as plantilla,
    ):
        for item in origen.infolist():
            texto = origen.read(item.filename).decode("utf-8")
            match item.filename:
                case "word/styles.xml":
                    texto = _reemplazar_estilos(texto)
                case "word/document.xml":
                    texto = re.sub(r"<w:sectPr>.*?</w:sectPr>", SECCION, texto, flags=re.S)
                case "word/_rels/document.xml.rels":
                    texto = texto.replace(
                        "</Relationships>",
                        '<Relationship Id="rIdPieHidalgo" Target="footer1.xml" Type="http://schemas.'
                        'openxmlformats.org/officeDocument/2006/relationships/footer"/></Relationships>',
                    )
                case "[Content_Types].xml":
                    texto = texto.replace(
                        "</Types>",
                        '<Default Extension="png" ContentType="image/png"/>'
                        '<Override PartName="/word/footer1.xml" ContentType="application/vnd.'
                        'openxmlformats-officedocument.wordprocessingml.footer+xml"/></Types>',
                    )
            plantilla.writestr(item, texto)
        plantilla.writestr("word/footer1.xml", _pie_de_pagina())


def documentos() -> list[tuple[Path, Path]]:
    """Pares (markdown de origen, word de destino)."""
    pares = [(DOCS / "guia-tecnica.md", SALIDA / "Guia-tecnica.docx")]
    for md in sorted((DOCS / "sesiones").glob("*.md")):
        pares.append((md, SALIDA / f"Sesion-{md.stem}.docx"))
    return pares


def _fecha_git(archivo: Path) -> str:
    """Fecha del último commit del archivo (o la actual si tiene cambios sin commitear).

    Se pasa a pandoc como SOURCE_DATE_EPOCH: si el Markdown no cambió, el Word generado es
    idéntico y git no lo marca como modificado.
    """
    modificado = _git("status", "--porcelain", "--", str(archivo))
    fecha = _git("log", "-1", "--format=%ct", "--", str(archivo))
    return fecha if fecha and not modificado else str(int(time.time()))


def _git(*argumentos: str) -> str:
    resultado = subprocess.run(["git", *argumentos], cwd=RAIZ, capture_output=True, text=True)
    return resultado.stdout.strip()


def convertir(md: Path, docx: Path, plantilla: Path) -> None:
    subprocess.run(
        [
            "pandoc", str(md),
            "--from", "gfm",  # mismo Markdown que muestra GitHub / VS Code
            "--to", "docx",
            "--reference-doc", str(plantilla),
            "--lua-filter", str(FILTRO_LUA),
            "--metadata", f"logo={marca.LOGO}",
            "--metadata", f"subtitulo={marca.NOMBRE_EMPRESA} · Gestión de Flota",
            "--resource-path", str(md.parent),
            "--output", str(docx),
        ],
        check=True,
        env={**os.environ, "SOURCE_DATE_EPOCH": _fecha_git(md)},
    )  # fmt: skip


def main() -> None:
    if shutil.which("pandoc") is None:
        sys.exit("No se encontró pandoc. Instalarlo con:  winget install JohnMacFarlane.Pandoc")
    SALIDA.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as temporal:
        plantilla = Path(temporal) / "plantilla-hidalgo.docx"
        crear_plantilla(plantilla)
        for md, docx in documentos():
            convertir(md, docx, plantilla)
            print(f"{md.relative_to(RAIZ)}  ->  {docx.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
