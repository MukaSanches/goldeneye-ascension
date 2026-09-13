#!/usr/bin/env python3
"""Generate the Ascension Learning Series PDFs from data/*.json.

The output is deliberately vector-first and asset-free: no game ROM, extracted
artwork, screenshots, or proprietary fonts are embedded. This keeps the course
set reproducible in CI and consistent with the repository's asset policy.
"""
from __future__ import annotations

import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import Paragraph
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
OUT = ROOT / "pdf"
OUT.mkdir(parents=True, exist_ok=True)

PAGE_W, PAGE_H = A4
BLACK = colors.HexColor("#0B0D10")
INK = colors.HexColor("#161A1F")
PAPER = colors.HexColor("#F3F0E8")
WHITE = colors.HexColor("#F8F6EF")
GOLD = colors.HexColor("#B99752")
GOLD_DARK = colors.HexColor("#806735")
RED = colors.HexColor("#A8332D")
MUTED = colors.HexColor("#7B7F83")
LINE = colors.HexColor("#D3CCBE")
PANEL = colors.HexColor("#EAE5D9")

styles = getSampleStyleSheet()
BODY = ParagraphStyle(
    "Body", parent=styles["BodyText"], fontName="Helvetica", fontSize=10.1,
    leading=14.2, textColor=INK, spaceAfter=6
)
H1 = ParagraphStyle(
    "H1", parent=BODY, fontName="Helvetica-Bold", fontSize=25,
    leading=28, textColor=INK, spaceAfter=8
)
H2 = ParagraphStyle(
    "H2", parent=BODY, fontName="Helvetica-Bold", fontSize=15,
    leading=18, textColor=INK, spaceAfter=6
)
BULLET = ParagraphStyle(
    "Bullet", parent=BODY, leftIndent=11, firstLineIndent=-8, bulletIndent=2,
    fontSize=9.6, leading=13.2, spaceAfter=4
)

def safe_text(value: str) -> str:
    replacements = {
        "–": "-", "—": "-", "“": '"', "”": '"', "’": "'", "→": "->",
        "•": "-", "…": "..."
    }
    for a, b in replacements.items():
        value = value.replace(a, b)
    return value


def p(text: str, style=BODY) -> Paragraph:
    return Paragraph(safe_text(text), style)


def draw_target(c: canvas.Canvas, x: float, y: float, r: float):
    c.saveState()
    c.setStrokeColor(GOLD)
    c.setLineWidth(1.2)
    for factor in (1.0, 0.70, 0.38):
        c.circle(x, y, r * factor, stroke=1, fill=0)
    c.line(x - r * 1.25, y, x + r * 1.25, y)
    c.line(x, y - r * 1.25, x, y + r * 1.25)
    c.restoreState()


def page_chrome(c: canvas.Canvas, course_id: str, section: str, page_no: int):
    c.setFillColor(PAPER)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    c.setFillColor(BLACK)
    c.rect(0, PAGE_H - 23 * mm, PAGE_W, 23 * mm, fill=1, stroke=0)
    c.setFillColor(GOLD)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(18 * mm, PAGE_H - 12.8 * mm, f"ASCENSION LEARNING SERIES / {course_id}")
    c.setFillColor(WHITE)
    c.setFont("Helvetica", 7.3)
    c.drawRightString(PAGE_W - 18 * mm, PAGE_H - 12.8 * mm, safe_text(section.upper()))
    c.setStrokeColor(LINE)
    c.line(18 * mm, 15 * mm, PAGE_W - 18 * mm, 15 * mm)
    c.setFont("Helvetica", 7)
    c.setFillColor(MUTED)
    c.drawString(18 * mm, 9.5 * mm, "ASCENSION / DOCUMENTACAO EDUCACIONAL")
    c.drawRightString(PAGE_W - 18 * mm, 9.5 * mm, f"{page_no:02d}")


def draw_paragraph(c, text, style, x, y, w, h=100 * mm):
    obj = p(text, style)
    _, ph = obj.wrap(w, h)
    obj.drawOn(c, x, y - ph)
    return y - ph


def draw_bullets(c, items, x, y, w, max_h=120 * mm):
    for item in items:
        obj = p("&bull; " + safe_text(item), BULLET)
        _, ph = obj.wrap(w, max_h)
        obj.drawOn(c, x, y - ph)
        y -= ph + 1.6 * mm
    return y


def draw_module(c, module, x, y, w, index):
    c.setFillColor(GOLD)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(x, y, f"MODULO {index:02d}")
    y -= 6 * mm
    title = p(module["title"], H2)
    _, h = title.wrap(w, 30 * mm)
    title.drawOn(c, x, y - h)
    y -= h + 3 * mm
    y = draw_bullets(c, module["bullets"], x, y, w)
    return y


def cover(c, course, series):
    c.setFillColor(BLACK)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    c.setFillColor(RED)
    c.rect(0, 0, 13 * mm, PAGE_H, fill=1, stroke=0)
    c.setFillColor(GOLD)
    c.rect(13 * mm, 0, 1.5 * mm, PAGE_H, fill=1, stroke=0)
    draw_target(c, PAGE_W - 44 * mm, PAGE_H - 51 * mm, 22 * mm)

    c.setFillColor(GOLD)
    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(27 * mm, PAGE_H - 36 * mm, f"COURSE {course['id']} / {course['category'].upper()}")

    title = p(course["title"], ParagraphStyle(
        "CoverTitle", parent=H1, fontSize=28, leading=31, textColor=WHITE, spaceAfter=0
    ))
    title.wrapOn(c, 132 * mm, 80 * mm)
    title.drawOn(c, 27 * mm, PAGE_H - 103 * mm)

    c.setStrokeColor(GOLD_DARK)
    c.setLineWidth(1)
    c.line(27 * mm, PAGE_H - 112 * mm, 108 * mm, PAGE_H - 112 * mm)

    summary = p(course["summary"], ParagraphStyle(
        "CoverSummary", parent=BODY, fontSize=11, leading=16, textColor=colors.HexColor("#D9D5CA")
    ))
    _, sh = summary.wrap(148 * mm, 75 * mm)
    summary.drawOn(c, 27 * mm, PAGE_H - 125 * mm - sh)

    c.setFillColor(colors.HexColor("#16191E"))
    c.roundRect(27 * mm, 34 * mm, 150 * mm, 34 * mm, 3 * mm, fill=1, stroke=0)
    c.setFillColor(GOLD)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(34 * mm, 57 * mm, "NIVEL")
    c.drawString(78 * mm, 57 * mm, "PUBLICO")
    c.drawString(160 * mm, 57 * mm, "EDICAO")
    c.setFillColor(WHITE)
    c.setFont("Helvetica", 8.2)
    c.drawString(34 * mm, 48 * mm, safe_text(course["level"]))
    audience = safe_text(course["audience"])
    c.drawString(78 * mm, 48 * mm, audience[:52])
    c.drawRightString(170 * mm, 48 * mm, series["edition"])

    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(WHITE)
    c.drawString(27 * mm, 20 * mm, "ASCENSION")
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 7)
    c.drawRightString(PAGE_W - 18 * mm, 20 * mm, "PRESERVAR O CLASSICO. ELEVAR A EXPERIENCIA.")


def objectives_page(c, course):
    page_chrome(c, course["id"], "Mapa do curso", 2)
    x, y, w = 18 * mm, PAGE_H - 38 * mm, PAGE_W - 36 * mm
    c.setFillColor(GOLD)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(x, y, "01 / ORIENTACAO")
    y -= 9 * mm
    y = draw_paragraph(c, "O que voce vai dominar", H1, x, y, w)
    y -= 6 * mm

    for i, obj in enumerate(course["objectives"], 1):
        c.setFillColor(PANEL)
        c.roundRect(x, y - 24 * mm, w, 20 * mm, 2.5 * mm, fill=1, stroke=0)
        c.setFillColor(RED)
        c.setFont("Helvetica-Bold", 18)
        c.drawString(x + 6 * mm, y - 16 * mm, f"{i:02d}")
        paragraph = p(obj, ParagraphStyle("Obj", parent=BODY, fontSize=10.4, leading=14, textColor=INK))
        _, ph = paragraph.wrap(w - 31 * mm, 16 * mm)
        paragraph.drawOn(c, x + 25 * mm, y - 9 * mm - ph)
        y -= 24 * mm

    y -= 4 * mm
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(x, y, "COMO USAR ESTE MATERIAL")
    y -= 7 * mm
    y = draw_bullets(c, [
        "Leia os conceitos antes do laboratorio; os exercicios foram desenhados para testar entendimento, nao memoria.",
        "Quando o curso citar o Ascension, confirme o estado atual no repositorio: documentacao e codigo sao a referencia viva.",
        "Nao trate uma afirmacao historica como fato apenas porque ela e repetida com frequencia; procure a fonte primaria quando possivel."
    ], x, y, w)


def modules_page(c, course, start_idx, page_no):
    page_chrome(c, course["id"], "Nucleo", page_no)
    x, y, w = 18 * mm, PAGE_H - 38 * mm, PAGE_W - 36 * mm
    c.setFillColor(GOLD)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(x, y, f"0{page_no - 1} / NUCLEO")
    y -= 9 * mm
    title = "Conceitos que sustentam a pratica" if start_idx == 0 else "Do conceito para a decisao"
    y = draw_paragraph(c, title, H1, x, y, w)
    y -= 7 * mm
    y = draw_module(c, course["modules"][start_idx], x, y, w, start_idx + 1)
    c.setStrokeColor(LINE)
    c.line(x, y - 2 * mm, x + w, y - 2 * mm)
    y -= 12 * mm
    draw_module(c, course["modules"][start_idx + 1], x, y, w, start_idx + 2)


def lab_page(c, course):
    page_chrome(c, course["id"], "Laboratorio", 5)
    x, y, w = 18 * mm, PAGE_H - 38 * mm, PAGE_W - 36 * mm
    c.setFillColor(GOLD)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(x, y, "04 / LABORATORIO")
    y -= 9 * mm
    y = draw_paragraph(c, "Teste o que aprendeu", H1, x, y, w)
    y -= 5 * mm
    c.setFillColor(INK)
    c.setFont("Helvetica", 9.5)
    c.drawString(x, y, "Execute na ordem. Registre resultado e duvida antes de repetir.")
    y -= 10 * mm
    for i, step in enumerate(course["lab"], 1):
        c.setFillColor(BLACK)
        c.roundRect(x, y - 32 * mm, w, 27 * mm, 3 * mm, fill=1, stroke=0)
        c.setFillColor(GOLD)
        c.setFont("Helvetica-Bold", 19)
        c.drawString(x + 7 * mm, y - 21 * mm, f"{i:02d}")
        paragraph = p(step, ParagraphStyle("Lab", parent=BODY, fontSize=10.1, leading=14.2, textColor=WHITE))
        _, ph = paragraph.wrap(w - 34 * mm, 22 * mm)
        paragraph.drawOn(c, x + 28 * mm, y - 10 * mm - ph)
        y -= 34 * mm

    c.setFillColor(PANEL)
    c.roundRect(x, 31 * mm, w, 38 * mm, 2.5 * mm, fill=1, stroke=0)
    c.setFillColor(RED)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(x + 6 * mm, 58 * mm, "REGISTRO DE CAMPO")
    y2 = 50 * mm
    c.setStrokeColor(LINE)
    for _ in range(4):
        c.line(x + 6 * mm, y2, x + w - 6 * mm, y2)
        y2 -= 7 * mm


def review_page(c, course):
    page_chrome(c, course["id"], "Revisao", 6)
    x, y, w = 18 * mm, PAGE_H - 38 * mm, PAGE_W - 36 * mm
    c.setFillColor(GOLD)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(x, y, "05 / REVISAO")
    y -= 9 * mm
    y = draw_paragraph(c, "Fechamento e proximo passo", H1, x, y, w)
    y -= 4 * mm
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(x, y, "PERGUNTAS DE REVISAO")
    y -= 7 * mm
    for i, q in enumerate(course["quiz"], 1):
        y = draw_paragraph(c, f"<b>{i:02d}.</b> {q}", BODY, x, y, w)
        y -= 5 * mm

    y -= 4 * mm
    c.setStrokeColor(LINE)
    c.line(x, y, x + w, y)
    y -= 10 * mm
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(x, y, "FONTES E PONTOS DE PARTIDA")
    y -= 8 * mm
    y = draw_bullets(c, course["references"], x, y, w)

    c.setFillColor(BLACK)
    c.roundRect(x, 32 * mm, w, 45 * mm, 3 * mm, fill=1, stroke=0)
    c.setFillColor(GOLD)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(x + 7 * mm, 65 * mm, "NOTA EDITORIAL")
    note = p(
        "Este curso e material educacional do projeto Ascension. Para assuntos tecnicos, o codigo e a documentacao atual do repositorio prevalecem sobre esta edicao. O projeto nao distribui ROM nem assets comerciais.",
        ParagraphStyle("Note", parent=BODY, fontSize=9.1, leading=13, textColor=WHITE)
    )
    _, nh = note.wrap(w - 14 * mm, 30 * mm)
    note.drawOn(c, x + 7 * mm, 58 * mm - nh)


def build_course(course, series):
    path = OUT / f"{course['id']}_{course['slug']}.pdf"
    c = canvas.Canvas(str(path), pagesize=A4, pageCompression=1)
    c.setTitle(course["title"])
    c.setAuthor("Ascension")
    c.setSubject("Ascension Learning Series")
    cover(c, course, series); c.showPage()
    objectives_page(c, course); c.showPage()
    modules_page(c, course, 0, 3); c.showPage()
    modules_page(c, course, 2, 4); c.showPage()
    lab_page(c, course); c.showPage()
    review_page(c, course); c.showPage()
    c.save()
    return path


def build_catalog(data):
    series = data["series"]
    courses = data["courses"]
    path = OUT / "00_CATALOGO_ASCENSION_LEARNING_SERIES.pdf"
    c = canvas.Canvas(str(path), pagesize=A4, pageCompression=1)
    c.setTitle("Catalogo Ascension Learning Series")
    c.setAuthor("Ascension")

    c.setFillColor(BLACK); c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    c.setFillColor(RED); c.rect(0, 0, 13 * mm, PAGE_H, fill=1, stroke=0)
    c.setFillColor(GOLD); c.rect(13 * mm, 0, 1.5 * mm, PAGE_H, fill=1, stroke=0)
    draw_target(c, PAGE_W - 47 * mm, PAGE_H - 55 * mm, 23 * mm)
    c.setFillColor(GOLD); c.setFont("Helvetica-Bold", 8.5)
    c.drawString(28 * mm, PAGE_H - 40 * mm, "EDITORIAL CATALOG / 20 COURSES")
    title = p("ASCENSION<br/>LEARNING SERIES", ParagraphStyle("Cat", parent=H1, fontSize=31, leading=34, textColor=WHITE))
    title.wrapOn(c, 130 * mm, 80 * mm); title.drawOn(c, 28 * mm, PAGE_H - 112 * mm)
    subtitle = p(series["tagline"], ParagraphStyle("Sub", parent=BODY, fontSize=11, leading=16, textColor=colors.HexColor("#D9D5CA")))
    _, h = subtitle.wrap(145 * mm, 50 * mm); subtitle.drawOn(c, 28 * mm, PAGE_H - 131 * mm - h)
    c.setFillColor(WHITE); c.setFont("Helvetica-Bold", 9)
    c.drawString(28 * mm, 24 * mm, f"EDICAO {series['edition']} / PT-BR")
    c.showPage()

    per_page = 10
    for page_index in range(2):
        page_chrome(c, "CATALOGO", "Indice", page_index + 2)
        x, y, w = 18 * mm, PAGE_H - 39 * mm, PAGE_W - 36 * mm
        c.setFillColor(GOLD); c.setFont("Helvetica-Bold", 8)
        c.drawString(x, y, f"0{page_index+1} / TRILHA")
        y -= 9 * mm
        y = draw_paragraph(c, "Cursos 01-10" if page_index == 0 else "Cursos 11-20", H1, x, y, w)
        y -= 4 * mm
        for course in courses[page_index * per_page:(page_index + 1) * per_page]:
            c.setFillColor(PANEL)
            c.roundRect(x, y - 18.5 * mm, w, 15.5 * mm, 2 * mm, fill=1, stroke=0)
            c.setFillColor(RED); c.setFont("Helvetica-Bold", 14)
            c.drawString(x + 5 * mm, y - 12 * mm, course["id"])
            c.setFillColor(INK); c.setFont("Helvetica-Bold", 9.2)
            title = safe_text(course["title"])
            if stringWidth(title, "Helvetica-Bold", 9.2) > w - 35 * mm:
                title = title[:73] + "..."
            c.drawString(x + 20 * mm, y - 8 * mm, title)
            c.setFillColor(MUTED); c.setFont("Helvetica", 7.5)
            c.drawString(x + 20 * mm, y - 13 * mm, f"{course['category']} / {course['level']}")
            y -= 18.5 * mm
        c.showPage()
    c.save()
    return path


def main():
    series = json.loads((DATA_DIR / "series.json").read_text(encoding="utf-8"))
    courses = [json.loads(path.read_text(encoding="utf-8")) for path in sorted(DATA_DIR.glob("[0-9][0-9].json"))]
    data = {"series": series, "courses": courses}
    produced = [build_catalog(data)]
    for course in courses:
        produced.append(build_course(course, series))
    print(f"generated {len(produced)} PDFs in {OUT}")
    for path in produced:
        print(path.name)


if __name__ == "__main__":
    main()
