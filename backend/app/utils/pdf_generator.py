import io
import calendar
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT


PRIMARY = colors.HexColor("#1E3A5F")
ACCENT = colors.HexColor("#2E86AB")
LIGHT = colors.HexColor("#EBF4F6")
WHITE = colors.white
DARK = colors.HexColor("#1A1A2E")


def generate_monthly_pdf(user: dict, expenses: list, summary: dict, month: int, year: int) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    story = []

    # Title
    title_style = ParagraphStyle("title", fontSize=20, textColor=PRIMARY,
                                  fontName="Helvetica-Bold", alignment=TA_CENTER)
    sub_style = ParagraphStyle("sub", fontSize=11, textColor=ACCENT,
                                fontName="Helvetica", alignment=TA_CENTER)
    body_style = ParagraphStyle("body", fontSize=10, textColor=DARK, fontName="Helvetica")

    story.append(Paragraph("Smart Expense Tracker", title_style))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        f"Monthly Report — {calendar.month_name[month]} {year}  |  {user.get('full_name', '')}",
        sub_style
    ))
    story.append(Spacer(1, 12))
    story.append(HRFlowable(width="100%", thickness=2, color=ACCENT))
    story.append(Spacer(1, 12))

    # Summary cards
    story.append(Paragraph("<b>Summary</b>", ParagraphStyle("h2", fontSize=13, textColor=PRIMARY,
                                                              fontName="Helvetica-Bold")))
    story.append(Spacer(1, 6))

    summary_data = [
        ["Total Spent", "Transactions", "Daily Average", "Budget Used"],
        [
            f"₹{summary.get('total_spent', 0):,.2f}",
            str(summary.get('transaction_count', 0)),
            f"₹{summary.get('avg_per_day', 0):,.2f}",
            f"{summary.get('budget_used_pct', 0):.1f}%",
        ]
    ]
    summary_table = Table(summary_data, colWidths=[4*cm, 4*cm, 4*cm, 4*cm])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWHEIGHT", (0, 0), (-1, -1), 24),
        ("BACKGROUND", (0, 1), (-1, 1), LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.5, ACCENT),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, ACCENT),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 18))

    # Expense table
    story.append(Paragraph("<b>Expense Details</b>", ParagraphStyle("h2", fontSize=13,
                                                                     textColor=PRIMARY, fontName="Helvetica-Bold")))
    story.append(Spacer(1, 6))

    headers = ["Date", "Title", "Category", "Payment", "Amount (₹)"]
    rows = [headers]
    for exp in expenses:
        date = str(exp.get("date", ""))[:10]
        rows.append([
            date,
            str(exp.get("title", ""))[:30],
            str(exp.get("category", "")),
            str(exp.get("payment_method", "")),
            f"{exp.get('amount', 0):,.2f}",
        ])

    # Add total row
    rows.append(["", "", "", "TOTAL", f"₹{summary.get('total_spent', 0):,.2f}"])

    expense_table = Table(rows, colWidths=[2.5*cm, 6*cm, 3*cm, 2.5*cm, 3*cm])
    ts = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (4, 0), (4, -1), "RIGHT"),
        ("ALIGN", (0, 0), (3, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWHEIGHT", (0, 0), (-1, -1), 20),
        ("BOX", (0, 0), (-1, -1), 0.5, ACCENT),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#C9DEE6")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("BACKGROUND", (0, -1), (-1, -1), LIGHT),
    ])
    # Alternate row shading
    for i in range(1, len(rows) - 1):
        if i % 2 == 0:
            ts.add("BACKGROUND", (0, i), (-1, i), LIGHT)
    expense_table.setStyle(ts)
    story.append(expense_table)

    doc.build(story)
    return buf.getvalue()
