from pathlib import Path
import argparse
import re
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageBreak,
    PageTemplate,
    Paragraph,
    Preformatted,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "INSTALLATION_GUIDE.md"
OUTPUT = ROOT / "docs" / "INSTALLATION_GUIDE.pdf"
INK = colors.HexColor("#18312f")
GREEN = colors.HexColor("#24735d")
GOLD = colors.HexColor("#c59a3b")
PALE = colors.HexColor("#f3f6f3")
RULE = colors.HexColor("#d8e0dc")
TEXT = colors.HexColor("#273331")


def inline_markup(value: str) -> str:
    value = escape(value)
    value = re.sub(r"`([^`]+)`", r'<font name="Courier" color="#235b4b">\1</font>', value)
    value = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", value)
    value = re.sub(r"\*(.+?)\*", r"<i>\1</i>", value)
    return value


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


class GuideDocument(BaseDocTemplate):
    def afterFlowable(self, flowable):
        if not isinstance(flowable, Paragraph):
            return
        level = {"SectionHeading": 0, "Subheading": 1}.get(flowable.style.name)
        if level is None:
            return
        title = flowable.getPlainText()
        key = slug(title)
        self.canv.bookmarkPage(key)
        self.canv.addOutlineEntry(title, key, level=level, closed=level > 0)
        self.notify("TOCEntry", (level, title, self.page, key))


def make_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="CoverTitle", parent=styles["Title"], fontName="Helvetica-Bold",
        fontSize=29, leading=34, textColor=INK, alignment=0, spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        name="CoverSubtitle", parent=styles["Normal"], fontName="Helvetica",
        fontSize=17, leading=22, textColor=GREEN, spaceAfter=18,
    ))
    styles.add(ParagraphStyle(
        name="CoverMeta", parent=styles["Normal"], fontSize=9, leading=14,
        textColor=TEXT, backColor=PALE, borderColor=RULE, borderWidth=0.6,
        borderPadding=10, spaceBefore=12,
    ))
    styles.add(ParagraphStyle(
        name="SectionHeading", parent=styles["Heading1"], fontName="Helvetica-Bold",
        fontSize=16, leading=20, textColor=INK, spaceBefore=14, spaceAfter=8,
        keepWithNext=True,
    ))
    styles.add(ParagraphStyle(
        name="Subheading", parent=styles["Heading2"], fontName="Helvetica-Bold",
        fontSize=11, leading=14, textColor=GREEN, spaceBefore=10, spaceAfter=5,
        keepWithNext=True,
    ))
    styles.add(ParagraphStyle(
        name="GuideBody", parent=styles["BodyText"], fontName="Helvetica",
        fontSize=8.7, leading=12.2, textColor=TEXT, spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name="GuideBullet", parent=styles["GuideBody"], leftIndent=13,
        firstLineIndent=-9, spaceAfter=3,
    ))
    styles.add(ParagraphStyle(
        name="GuideQuote", parent=styles["GuideBody"], leftIndent=9,
        borderColor=GOLD, borderWidth=2, borderPadding=7,
        backColor=PALE, spaceBefore=5, spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        name="GuideCode", fontName="Courier", fontSize=7.6, leading=10,
        textColor=INK, backColor=PALE, borderColor=RULE, borderWidth=0.5,
        borderPadding=7, leftIndent=5, rightIndent=5, spaceBefore=3, spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        name="TableText", parent=styles["GuideBody"], fontSize=7.2,
        leading=9.2, spaceAfter=1,
    ))
    styles.add(ParagraphStyle(
        name="TableHeader", parent=styles["TableText"], fontName="Helvetica-Bold",
        textColor=colors.white,
    ))
    styles.add(ParagraphStyle(
        name="ContentsTitle", parent=styles["Heading1"], fontName="Helvetica-Bold",
        fontSize=21, leading=26, textColor=INK, spaceAfter=12,
    ))
    return styles


def parse_table(rows, styles, page_width):
    parsed = []
    for row_index, row in enumerate(rows):
        style = styles["TableHeader"] if row_index == 0 else styles["TableText"]
        parsed.append([Paragraph(inline_markup(cell.strip()), style) for cell in row])
    count = len(parsed[0])
    if count == 5 and rows[0][0].strip().lower() == "method":
        ratios = [0.10, 0.21, 0.23, 0.31, 0.15]
    elif count == 5:
        ratios = [0.18, 0.20, 0.13, 0.20, 0.29]
    else:
        ratios = {
            2: [0.25, 0.75],
            3: [0.20, 0.35, 0.45],
            4: [0.22, 0.26, 0.24, 0.28],
        }.get(count, [1 / count] * count)
    table = Table(
        parsed,
        colWidths=[page_width * ratio for ratio in ratios],
        repeatRows=1,
        hAlign="LEFT",
        splitByRow=1,
    )
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), INK),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE]),
        ("GRID", (0, 0), (-1, -1), 0.35, RULE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def build_story(markdown, styles, page_width, subtitle, description, cover_metadata):
    lines = markdown.splitlines()
    story = [
        Spacer(1, 35 * mm),
        Paragraph("AI RESEARCH<br/>KNOWLEDGE HUB", styles["CoverTitle"]),
        Paragraph(escape(subtitle), styles["CoverSubtitle"]),
        Table([[""]], colWidths=[48 * mm], rowHeights=[2], style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), GOLD),
        ])),
        Spacer(1, 12 * mm),
        Paragraph(
            escape(description),
            styles["GuideBody"],
        ),
        Spacer(1, 10 * mm),
        Paragraph(
            escape(cover_metadata).replace("\n", "<br/>"),
            styles["CoverMeta"],
        ),
        PageBreak(),
        Paragraph("Contents", styles["ContentsTitle"]),
    ]
    toc = TableOfContents()
    toc.levelStyles = [
        ParagraphStyle(name="TOC0", fontName="Helvetica-Bold", fontSize=9.2, leading=14, textColor=INK, leftIndent=0, firstLineIndent=0, spaceBefore=3),
        ParagraphStyle(name="TOC1", fontName="Helvetica", fontSize=8, leading=11, textColor=GREEN, leftIndent=15, firstLineIndent=0),
    ]
    story.extend([toc, PageBreak()])

    index = 0
    in_contents = False
    in_code = False
    code_lines = []
    table_rows = []

    def flush_table():
        nonlocal table_rows
        if table_rows:
            story.append(parse_table(table_rows, styles, page_width))
            story.append(Spacer(1, 5))
            table_rows = []

    while index < len(lines):
        stripped = lines[index].strip()

        if stripped.lower() == "# ai research knowledge hub" or stripped in {"## Installation Guide", "## Project Report"}:
            index += 1
            continue
        if stripped == "## Contents":
            in_contents = True
            index += 1
            continue
        if in_contents:
            if re.match(r"^## (?:\d+(?:\.\d+)?[.)]?\s|Appendix [A-Z])", stripped):
                in_contents = False
            else:
                index += 1
                continue

        if stripped.startswith("```"):
            flush_table()
            if in_code:
                story.append(Preformatted("\n".join(code_lines), styles["GuideCode"], maxLineLength=100))
                code_lines = []
            in_code = not in_code
            index += 1
            continue
        if in_code:
            code_lines.append(lines[index])
            index += 1
            continue

        if stripped.startswith("|"):
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in cells):
                index += 1
                continue
            table_rows.append(cells)
            index += 1
            continue
        flush_table()

        if not stripped or stripped == "---":
            index += 1
            continue
        if stripped.startswith("> "):
            story.append(Paragraph(inline_markup(stripped[2:]), styles["GuideQuote"]))
        elif stripped.startswith("### "):
            story.append(Paragraph(inline_markup(stripped[4:]), styles["Subheading"]))
        elif stripped.startswith("## "):
            story.append(Paragraph(inline_markup(stripped[3:]), styles["SectionHeading"]))
        elif stripped.startswith("# "):
            story.append(Paragraph(inline_markup(stripped[2:]), styles["SectionHeading"]))
        elif stripped.startswith("- "):
            story.append(Paragraph(inline_markup(stripped[2:]), styles["GuideBullet"], bulletText="-"))
        else:
            story.append(Paragraph(inline_markup(stripped), styles["GuideBody"]))
        index += 1

    flush_table()
    if in_code and code_lines:
        story.append(Preformatted("\n".join(code_lines), styles["GuideCode"], maxLineLength=100))
    return story


def draw_page(canvas, document):
    canvas.saveState()
    width, height = A4
    if document.page > 1:
        canvas.setStrokeColor(RULE)
        canvas.setLineWidth(0.5)
        canvas.line(18 * mm, height - 15 * mm, width - 18 * mm, height - 15 * mm)
        canvas.setFont("Helvetica-Bold", 7.5)
        canvas.setFillColor(INK)
        canvas.drawString(18 * mm, height - 11.5 * mm, "AI RESEARCH KNOWLEDGE HUB")
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(GREEN)
        canvas.drawRightString(width - 18 * mm, height - 11.5 * mm, getattr(document, "running_title", "INSTALLATION GUIDE"))
    canvas.setStrokeColor(RULE)
    canvas.line(18 * mm, 14 * mm, width - 18 * mm, 14 * mm)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#5b6864"))
    canvas.drawString(18 * mm, 9 * mm, "Repository-verified documentation")
    canvas.drawRightString(width - 18 * mm, 9 * mm, f"Page {document.page}")
    canvas.restoreState()


def main():
    parser = argparse.ArgumentParser(description="Render a Markdown project document as a styled PDF.")
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--subtitle", default="Installation Guide")
    parser.add_argument("--running-title", default="INSTALLATION GUIDE")
    parser.add_argument("--description", default="A repository-verified guide to installing, configuring, running, and validating the application.")
    parser.add_argument("--cover-metadata", default="Audience: Developers and system administrators\nBasis: Current project source and configuration\nUnverified deployment values are identified explicitly.")
    args = parser.parse_args()

    styles = make_styles()
    width = A4[0] - 36 * mm
    document = GuideDocument(
        str(args.output),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=22 * mm,
        bottomMargin=20 * mm,
        title=f"AI Research Knowledge Hub - {args.subtitle}",
        author="AI Research Knowledge Hub Project",
    )
    document.running_title = args.running_title
    frame = Frame(document.leftMargin, document.bottomMargin, width, A4[1] - 42 * mm, id="content")
    document.addPageTemplates([PageTemplate(id="guide", frames=[frame], onPage=draw_page)])
    story = build_story(args.source.read_text(encoding="utf-8"), styles, width, args.subtitle, args.description, args.cover_metadata)
    document.multiBuild(story)
    print(f"Created {args.output}")


if __name__ == "__main__":
    main()