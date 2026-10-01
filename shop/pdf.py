from datetime import timedelta
from io import BytesIO

from django.conf import settings
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

NAVY, RED, GREEN = colors.HexColor("#1e1e4b"), colors.HexColor("#d40000"), colors.HexColor("#0b6b1e")


def _render(label, ref, info, lines, total, show_payment, note):
    """lines: [(name, qty, unit_price, line_total)]; info: [(label, value)]."""
    shop = settings.SHOP
    sym = shop["CURRENCY_SYMBOL"]
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm,
                            bottomMargin=16 * mm, title=f"{label.title()} {ref}", author=shop["ORG"])
    ss = getSampleStyleSheet()
    h = ParagraphStyle("h", parent=ss["Title"], textColor=NAVY, alignment=0, fontSize=20, spaceAfter=2)
    small = ParagraphStyle("s", parent=ss["Normal"], fontSize=9, textColor=colors.HexColor("#555555"), leading=12)
    body = ParagraphStyle("b", parent=ss["Normal"], fontSize=10, leading=14)
    bold = ParagraphStyle("bb", parent=body, fontName="Helvetica-Bold")

    logo = Image(str(settings.BASE_DIR / "static" / "img" / "mcz-logo.jpg"), 22 * mm, 22 * mm)
    head = Table([[logo, [Paragraph(shop["NAME"], h), Paragraph(f"{shop['ORG']} · {shop['CHURCH']}", small)],
                   [Paragraph(label, bold), Paragraph(ref, h)]]], colWidths=[26 * mm, 100 * mm, 48 * mm])
    head.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LINEBELOW", (0, 0), (-1, 0), 2, RED),
                              ("BOTTOMPADDING", (0, 0), (-1, 0), 8)]))

    info_t = Table([[Paragraph(k, bold), Paragraph(str(v).replace("\n", "<br/>"), body)] for k, v in info],
                   colWidths=[32 * mm, 142 * mm])
    info_t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))

    rows = [["Item", "Qty", "Price", "Total"]]
    for name, qty, price, line in lines:
        rows.append([Paragraph(name, body), qty, f"{sym}{price:.2f}", f"{sym}{line:.2f}"])
    rows.append(["", "", "Total", f"{sym}{total:.2f}"])
    items = Table(rows, colWidths=[104 * mm, 16 * mm, 27 * mm, 27 * mm], repeatRows=1)
    items.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#f4f4fa")]),
        ("LINEABOVE", (0, -1), (-1, -1), 1, NAVY), ("FONTNAME", (2, -1), (-1, -1), "Helvetica-Bold"),
        ("TEXTCOLOR", (3, -1), (3, -1), GREEN), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))

    pay = [Paragraph("How to pay", bold), Paragraph(shop["PAYMENT_INSTRUCTIONS"], body), Spacer(1, 3)]
    pay_rows = [[Paragraph(k, bold), Paragraph(v, body)] for k, v in shop["BANK"].items()]
    pay_rows.append([Paragraph("EcoCash", bold), Paragraph(f"{shop['ECOCASH_NUMBER']} ({shop['ECOCASH_NAME']})", body)])
    pay_t = Table(pay_rows, colWidths=[40 * mm, 100 * mm])
    pay_t.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.8, GREEN), ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eef8f0"))]))

    story = [head, Spacer(1, 8), info_t, Spacer(1, 10), items, Spacer(1, 14)]
    if show_payment:
        story += pay + [pay_t, Spacer(1, 4), Paragraph(note, small)]
    story += [Spacer(1, 14), Paragraph(f"Thank you for supporting the {shop['ORG']}. God bless you.", small)]
    doc.build(story)
    return buf.getvalue()


def order_pdf(order):
    info = [("Date", order.created.strftime("%d %b %Y %H:%M")), ("Status", order.get_status_display()),
            ("Name", order.full_name), ("Email", order.email), ("Phone", order.phone)]
    if order.has_physical:
        info.append(("Deliver to", f"{order.address}, {order.city}"))
    if order.payment_reference:
        info.append(("Payment ref", order.payment_reference))
    lines = [(i.product.name, i.quantity, i.price, i.line_total) for i in order.items.select_related("product")]
    return _render("ORDER", order.short_id, info, lines, order.total, order.status == order.PENDING,
                   "Send your proof of payment (PoP) with your order reference.")


def quote_pdf(user, items, total):
    """items: Cart.items() dicts. A price quote valid for 7 days; no order is created."""
    now = timezone.localtime()
    info = [("Date", now.strftime("%d %b %Y")), ("Valid until", (now + timedelta(days=7)).strftime("%d %b %Y")),
            ("Prepared for", user.get_full_name() or user.username), ("Email", user.email or "—")]
    lines = [(i["product"].name, i["quantity"], i["product"].price, i["line_total"]) for i in items]
    ref = "Q-" + now.strftime("%y%m%d-%H%M")
    return _render("QUOTE", ref, info, lines, total, True,
                   "This is a quote, not an order. Place your order on the website, then pay and send your proof of payment (PoP).")
