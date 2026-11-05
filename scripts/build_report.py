#!/usr/bin/env python3
"""Build the final technical report PDF from docs/technical_report.md."""

from __future__ import annotations

import html
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.platypus import (
    Flowable,
    CondPageBreak,
    Image,
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "technical_report.md"
OUTPUT = ROOT / "output" / "pdf" / "nyc_mobility_technical_report.pdf"

NAVY = colors.HexColor("#12233F")
BLUE = colors.HexColor("#168AAD")
LIGHT_BLUE = colors.HexColor("#E8F4FB")
ORANGE = colors.HexColor("#D97706")
GREEN = colors.HexColor("#2F855A")
TEXT = colors.HexColor("#27364D")
MUTED = colors.HexColor("#53657D")
LIGHT = colors.HexColor("#F5F8FC")


class ArchitectureDiagram(Flowable):
    def __init__(self, width: float = 170 * mm, height: float = 72 * mm):
        super().__init__()
        self.width = width
        self.height = height

    def draw(self):
        canvas = self.canv
        boxes = [
            (0, 35, 36, 28, "NYC TLC", "20 Parquet files", ORANGE),
            (44, 35, 36, 28, "Downloader", "validated files", BLUE),
            (88, 35, 36, 28, "Airflow", "schedule/backfill", BLUE),
            (132, 35, 38, 28, "DuckDB", "facts + dimensions", ORANGE),
            (65, 0, 43, 25, "SQL analytics", "10 queries", GREEN),
            (118, 0, 52, 25, "Superset", "read-only dashboard", GREEN),
        ]
        scale_x = self.width / (170 * mm)
        scale_y = self.height / (72 * mm)

        def sx(value):
            return value * mm * scale_x

        def sy(value):
            return value * mm * scale_y

        for x, y, width, height, title, subtitle, color in boxes:
            canvas.setFillColor(colors.white)
            canvas.setStrokeColor(color)
            canvas.setLineWidth(1.6)
            canvas.roundRect(sx(x), sy(y), sx(width), sy(height), 4 * mm, fill=1)
            canvas.setFillColor(NAVY)
            canvas.setFont("Helvetica-Bold", 9)
            canvas.drawCentredString(sx(x + width / 2), sy(y + height - 10), title)
            canvas.setFillColor(MUTED)
            canvas.setFont("Helvetica", 7.5)
            canvas.drawCentredString(sx(x + width / 2), sy(y + 7), subtitle)

        canvas.setStrokeColor(MUTED)
        canvas.setLineWidth(1.2)
        for start, end in [((36, 49), (44, 49)), ((80, 49), (88, 49)), ((124, 49), (132, 49))]:
            canvas.line(sx(start[0]), sy(start[1]), sx(end[0]), sy(end[1]))
        canvas.line(sx(150), sy(35), sx(150), sy(25))
        canvas.line(sx(140), sy(25), sx(140), sy(35))
        canvas.line(sx(132), sy(35), sx(105), sy(25))


class ModelDiagram(Flowable):
    def __init__(self, width: float = 170 * mm, height: float = 88 * mm):
        super().__init__()
        self.width = width
        self.height = height

    def draw(self):
        canvas = self.canv
        scale_x = self.width / (170 * mm)
        scale_y = self.height / (88 * mm)

        def sx(value):
            return value * mm * scale_x

        def sy(value):
            return value * mm * scale_y

        items = [
            (0, 55, 42, 25, "dim_zone", "zone, borough, name", BLUE),
            (0, 20, 42, 25, "dim_provider", "license + base", BLUE),
            (63, 32, 48, 48, "fact_trips", "one accepted trip\n21 analytical columns", ORANGE),
            (128, 55, 42, 25, "dim_ride_features", "sharing, AAR, WAV", BLUE),
            (45, 0, 58, 19, "quarantined_trips", "source row + reason list", GREEN),
            (111, 0, 59, 19, "dashboard aggregates", "interactive workload", GREEN),
        ]
        for x, y, width, height, title, subtitle, color in items:
            canvas.setFillColor(colors.white)
            canvas.setStrokeColor(color)
            canvas.setLineWidth(1.5)
            canvas.roundRect(sx(x), sy(y), sx(width), sy(height), 3 * mm, fill=1)
            canvas.setFillColor(NAVY)
            canvas.setFont("Helvetica-Bold", 8.5)
            canvas.drawCentredString(sx(x + width / 2), sy(y + height - 8), title)
            canvas.setFillColor(MUTED)
            canvas.setFont("Helvetica", 7)
            for line_number, line in enumerate(subtitle.split("\n")):
                canvas.drawCentredString(
                    sx(x + width / 2), sy(y + 7 + 5 * (len(subtitle.split("\n")) - line_number - 1)), line
                )
        canvas.setStrokeColor(MUTED)
        canvas.setLineWidth(1.2)
        canvas.line(sx(42), sy(67), sx(63), sy(67))
        canvas.line(sx(42), sy(32), sx(63), sy(50))
        canvas.line(sx(111), sy(67), sx(128), sy(67))
        canvas.line(sx(87), sy(32), sx(74), sy(19))
        canvas.line(sx(96), sy(32), sx(131), sy(19))


def inline_markup(text: str) -> str:
    escaped = html.escape(text, quote=False)
    escaped = re.sub(r"`([^`]+)`", r'<font name="Courier">\1</font>', escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", escaped)
    escaped = re.sub(r"&lt;(https?://[^&]+)&gt;", r'<link href="\1" color="#168AAD">\1</link>', escaped)
    return escaped


def parse_table(lines: list[str], styles: dict[str, ParagraphStyle]) -> Table:
    rows = []
    for line in lines:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if all(set(cell) <= {"-", ":"} for cell in cells):
            continue
        cell_style = styles["table_header"] if not rows else styles["table"]
        rows.append([Paragraph(inline_markup(cell), cell_style) for cell in cells])
    column_count = max(len(row) for row in rows)
    widths = [170 * mm / column_count] * column_count
    table = Table(rows, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#C7D2E0")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def build_story(styles: dict[str, ParagraphStyle]):
    story = []
    story.extend(
        [
            Spacer(1, 40 * mm),
            Paragraph("NYC Mobility Analytics Platform", styles["cover_title"]),
            Spacer(1, 8 * mm),
            Paragraph("Technical report", styles["cover_subtitle"]),
            Spacer(1, 24 * mm),
            Table(
                [
                    ["Dataset", "Official NYC TLC HVFHV trip records"],
                    ["Coverage", "January 2025 - August 2026"],
                    ["Scale", "411,776,395 source rows / 10.042 GB"],
                    ["Platform", "DuckDB, Airflow, Superset, Docker Compose"],
                    ["Date", "5 November 2026"],
                ],
                colWidths=[38 * mm, 105 * mm],
                hAlign="CENTER",
                style=TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (0, -1), NAVY),
                        ("TEXTCOLOR", (0, 0), (0, -1), colors.white),
                        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                        ("BACKGROUND", (1, 0), (1, -1), LIGHT_BLUE),
                        ("TEXTCOLOR", (1, 0), (1, -1), TEXT),
                        ("GRID", (0, 0), (-1, -1), 0.6, colors.white),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 9),
                        ("TOPPADDING", (0, 0), (-1, -1), 8),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ]
                ),
            ),
            PageBreak(),
            Paragraph("Contents", styles["h1"]),
            Paragraph(
                "Executive summary  /  Business context  /  Data sources  /  Architecture  /  Warehouse design  /  Data quality  /  Orchestration  /  Performance  /  SQL analytics  /  Superset dashboard  /  Deployment  /  Limitations  /  Reproduction  /  References",
                styles["body"],
            ),
            Spacer(1, 8 * mm),
            Paragraph("Verified headline metrics", styles["h2"]),
            Table(
                [
                    ["Raw rows", "Accepted", "Quarantined", "Difference"],
                    ["411,776,395", "411,739,486", "36,909", "0"],
                ],
                colWidths=[42.5 * mm] * 4,
                style=TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("BACKGROUND", (0, 1), (-1, 1), LIGHT_BLUE),
                        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.white),
                        ("TOPPADDING", (0, 0), (-1, -1), 8),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ]
                ),
            ),
            PageBreak(),
        ]
    )

    lines = SOURCE.read_text(encoding="utf-8").splitlines()[3:]
    index = 0
    paragraph_buffer: list[str] = []

    def flush_paragraph():
        if paragraph_buffer:
            story.append(Paragraph(inline_markup(" ".join(paragraph_buffer)), styles["body"]))
            story.append(Spacer(1, 2.5 * mm))
            paragraph_buffer.clear()

    while index < len(lines):
        line = lines[index].rstrip()
        if not line:
            flush_paragraph()
            index += 1
            continue
        if line.startswith("!["):
            flush_paragraph()
            if "architecture.svg" in line:
                story.extend([ArchitectureDiagram(), Spacer(1, 5 * mm)])
            elif "dimensional-model.svg" in line:
                story.extend([ModelDiagram(), Spacer(1, 5 * mm)])
            elif "superset-dashboard.png" in line:
                screenshot = ROOT / "docs" / "images" / "superset-dashboard.png"
                story.extend(
                    [
                        Spacer(1, 2 * mm),
                        Image(str(screenshot), width=170 * mm, height=95.625 * mm),
                        Paragraph("Figure 3. Live unfiltered Superset dashboard with native filters and warehouse-backed charts.", styles["caption"]),
                        Spacer(1, 5 * mm),
                    ]
                )
            index += 1
            continue
        if line.startswith("## "):
            flush_paragraph()
            heading = line[3:]
            if heading == "Technical architecture":
                story.append(CondPageBreak(90 * mm))
            elif heading == "Reproduction checklist":
                story.append(CondPageBreak(80 * mm))
            else:
                story.append(CondPageBreak(35 * mm))
            story.append(Paragraph(inline_markup(heading), styles["h1"]))
            index += 1
            continue
        if line.startswith("### "):
            flush_paragraph()
            story.append(Paragraph(inline_markup(line[4:]), styles["h2"]))
            index += 1
            continue
        if line.startswith("|"):
            flush_paragraph()
            table_lines = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                table_lines.append(lines[index])
                index += 1
            story.extend([KeepTogether(parse_table(table_lines, styles)), Spacer(1, 4 * mm)])
            continue
        if line.startswith("- "):
            flush_paragraph()
            bullets = []
            while index < len(lines) and lines[index].startswith("- "):
                bullets.append(
                    [
                        Paragraph("&#8226;", styles["bullet_marker"]),
                        Paragraph(inline_markup(lines[index][2:]), styles["bullet_body"]),
                    ]
                )
                index += 1
            story.append(
                Table(
                    bullets,
                    colWidths=[6 * mm, 164 * mm],
                    hAlign="LEFT",
                    style=TableStyle(
                        [
                            ("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("LEFTPADDING", (0, 0), (-1, -1), 0),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                            ("TOPPADDING", (0, 0), (-1, -1), 1.5),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
                        ]
                    ),
                )
            )
            story.append(Spacer(1, 3 * mm))
            continue
        if re.match(r"^\d+\. ", line):
            flush_paragraph()
            items = []
            while index < len(lines) and re.match(r"^\d+\. ", lines[index]):
                items.append(
                    ListItem(
                        Paragraph(inline_markup(re.sub(r"^\d+\. ", "", lines[index])), styles["body"]),
                        leftIndent=5 * mm,
                    )
                )
                index += 1
            story.append(KeepTogether(ListFlowable(items, bulletType="1", leftIndent=8 * mm, bulletColor=BLUE)))
            story.append(Spacer(1, 3 * mm))
            continue
        paragraph_buffer.append(line)
        index += 1
    flush_paragraph()
    return story


def on_page(canvas, document):
    page = canvas.getPageNumber()
    if page == 1:
        canvas.setFillColor(NAVY)
        canvas.rect(0, 0, 18 * mm, A4[1], fill=1, stroke=0)
        canvas.setFillColor(BLUE)
        canvas.rect(18 * mm, 0, 4 * mm, A4[1], fill=1, stroke=0)
        return
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#D8E1EC"))
    canvas.line(20 * mm, 18 * mm, A4[0] - 20 * mm, 18 * mm)
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(20 * mm, 11 * mm, "NYC Mobility Analytics Platform")
    canvas.drawRightString(A4[0] - 20 * mm, 11 * mm, f"Page {page}")
    canvas.restoreState()


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    sample = getSampleStyleSheet()
    styles = {
        "cover_title": ParagraphStyle(
            "CoverTitle", parent=sample["Title"], fontName="Helvetica-Bold", fontSize=30,
            leading=36, textColor=NAVY, alignment=TA_CENTER, spaceAfter=8
        ),
        "cover_subtitle": ParagraphStyle(
            "CoverSubtitle", parent=sample["Normal"], fontName="Helvetica", fontSize=16,
            leading=22, textColor=BLUE, alignment=TA_CENTER
        ),
        "h1": ParagraphStyle(
            "H1", parent=sample["Heading1"], fontName="Helvetica-Bold", fontSize=18,
            leading=22, textColor=NAVY, keepWithNext=True, spaceBefore=14, spaceAfter=6
        ),
        "h2": ParagraphStyle(
            "H2", parent=sample["Heading2"], fontName="Helvetica-Bold", fontSize=13,
            leading=17, textColor=BLUE, keepWithNext=True, spaceBefore=9, spaceAfter=4
        ),
        "body": ParagraphStyle(
            "Body", parent=sample["BodyText"], fontName="Helvetica", fontSize=9.6,
            leading=14, textColor=TEXT, alignment=TA_LEFT, spaceAfter=3
        ),
        "bullet_marker": ParagraphStyle(
            "BulletMarker", parent=sample["BodyText"], fontName="Helvetica-Bold", fontSize=9.6,
            leading=14, textColor=BLUE, alignment=TA_LEFT
        ),
        "bullet_body": ParagraphStyle(
            "BulletBody", parent=sample["BodyText"], fontName="Helvetica", fontSize=9.6,
            leading=14, textColor=TEXT, alignment=TA_LEFT
        ),
        "caption": ParagraphStyle(
            "Caption", parent=sample["BodyText"], fontName="Helvetica-Oblique", fontSize=8,
            leading=11, textColor=MUTED, alignment=TA_CENTER, spaceBefore=3
        ),
        "table": ParagraphStyle(
            "Table", parent=sample["BodyText"], fontName="Helvetica", fontSize=8.1,
            leading=10.5, textColor=TEXT
        ),
        "table_header": ParagraphStyle(
            "TableHeader", parent=sample["BodyText"], fontName="Helvetica-Bold", fontSize=8.1,
            leading=10.5, textColor=colors.white
        ),
    }
    document = SimpleDocTemplate(
        str(OUTPUT), pagesize=A4, rightMargin=20 * mm, leftMargin=20 * mm,
        topMargin=20 * mm, bottomMargin=23 * mm, title="NYC Mobility Analytics Platform",
        author="Qeema Internship Project",
    )
    document.build(build_story(styles), onFirstPage=on_page, onLaterPages=on_page)
    print(OUTPUT)


if __name__ == "__main__":
    main()
