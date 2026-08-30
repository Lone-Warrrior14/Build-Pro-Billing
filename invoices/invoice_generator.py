"""
BuildPro tax invoice PDF generator.
Clean, professional layout that perfectly fits within page margins.
Removes duplicate outer box overflows and awkward line overlaps.
"""
from __future__ import annotations

import os

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, Flowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

from database.models import Invoice
from utils.money import amount_in_words, to_rupees


def resolve_image_path(path: str | None) -> str | None:
    if not path:
        return None
    if os.path.isabs(path) and os.path.exists(path):
        return path

    import sys
    from database.connection import get_app_dir
    app_dir = get_app_dir()

    candidates = [
        path,
        os.path.join(app_dir, path),
        os.path.join(app_dir, "static", os.path.basename(path)),
        os.path.join(app_dir, "assets", os.path.basename(path)),
        os.path.join(app_dir, os.path.basename(path)),
    ]

    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", app_dir)
        candidates.extend([
            os.path.join(meipass, path),
            os.path.join(meipass, "static", os.path.basename(path)),
            os.path.join(meipass, "assets", os.path.basename(path)),
            os.path.join(meipass, os.path.basename(path)),
        ])

        exe_dir = os.path.dirname(sys.executable)
        candidates.extend([
            os.path.join(exe_dir, path),
            os.path.join(exe_dir, "static", os.path.basename(path)),
            os.path.join(exe_dir, os.path.basename(path)),
        ])

    for c in candidates:
        if c and os.path.exists(c):
            return c
    return None


class OverlaidSealSign(Flowable):
    """Flowable that renders seal.png with sign.png superimposed centered over it."""
    def __init__(self, seal_path, sign_path, width=32*mm, height=32*mm):
        super().__init__()
        r_seal = resolve_image_path(seal_path)
        r_sign = resolve_image_path(sign_path)
        self.seal_path = r_seal if (r_seal and os.path.exists(r_seal)) else None
        self.sign_path = r_sign if (r_sign and os.path.exists(r_sign)) else None
        self.width = width
        self.height = height

    def wrap(self, availWidth, availHeight):
        return self.width, self.height

    def draw(self):
        self.canv.saveState()
        # Draw Seal
        if self.seal_path:
            self.canv.drawImage(self.seal_path, 0, 0, width=self.width, height=self.height, mask='auto')
        # Draw Signature in the center over the seal
        if self.sign_path:
            sign_w = self.width * 0.75
            sign_h = self.height * 0.45
            x_off = (self.width - sign_w) / 2.0
            y_off = (self.height - sign_h) / 2.0
            self.canv.drawImage(self.sign_path, x_off, y_off, width=sign_w, height=sign_h, mask='auto')
        self.canv.restoreState()


def _safe_image(path, width, height):
    resolved = resolve_image_path(path)
    if resolved and os.path.exists(resolved):
        try:
            return Image(resolved, width=width, height=height)
        except Exception:
            return None
    return None


def generate_invoice_pdf(invoice: Invoice, output_path: str, is_sealed: bool | None = None) -> str:
    if is_sealed is None:
        is_sealed = getattr(invoice, "is_sealed", False)
    styles = getSampleStyleSheet()

    company_title_style = ParagraphStyle(
        "CompanyTitle", parent=styles["Heading1"], alignment=TA_CENTER, fontSize=14, leading=16, fontName="Helvetica-Bold"
    )
    sub_title_style = ParagraphStyle(
        "CompanySubtitle", parent=styles["Normal"], alignment=TA_CENTER, fontSize=9, leading=11, fontName="Helvetica-Bold"
    )
    tax_invoice_style = ParagraphStyle(
        "TaxInvoice", parent=styles["Heading2"], alignment=TA_CENTER, fontSize=12, leading=14, fontName="Helvetica-Bold",
        textColor=colors.HexColor("#1e3a8a")
    )
    small_center = ParagraphStyle(
        "SmallCenter", parent=styles["Normal"], alignment=TA_CENTER, fontSize=8, leading=10
    )
    normal = ParagraphStyle("NormalText", parent=styles["Normal"], fontSize=9, leading=12)
    right_align = ParagraphStyle("RightText", parent=normal, alignment=TA_RIGHT)
    bold_right = ParagraphStyle("BoldRightText", parent=normal, alignment=TA_RIGHT, fontName="Helvetica-Bold")

    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=10 * mm, rightMargin=10 * mm, topMargin=10 * mm, bottomMargin=10 * mm,
    )
    story = []

    # 1. Top Centered Logo
    logo_path = resolve_image_path(invoice.logo_path_snapshot or "bill logo.png")
    logo_img = _safe_image(logo_path, 110 * mm, 30 * mm)
    if logo_img:
        logo_table = Table([[logo_img]], colWidths=[190 * mm])
        logo_table.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(logo_table)
    else:
        story.append(Paragraph("<b>BUILD PRO READY MIX</b>", company_title_style))
        story.append(Paragraph("<b>SOLUTION FOR CONSTRUCTION WORK</b>", sub_title_style))

    # 2. TAX INVOICE bar
    tax_bar_table = Table([[Paragraph("TAX INVOICE", tax_invoice_style)]], colWidths=[190 * mm])
    tax_bar_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("LINEABOVE", (0, 0), (-1, -1), 1, colors.black),
        ("LINEBELOW", (0, 0), (-1, -1), 1, colors.black),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(tax_bar_table)

    # 3. Company Banner Block (Light Blue Fill)
    comp_title = Paragraph("BUILD PRO READY MIX", company_title_style)
    comp_addr = invoice.company_address_snapshot or "HO: No. 3-58/B, Mariam Commercial Complex, Permude, Mangalore - 574509"
    if "Branch:" in comp_addr:
        comp_addr = comp_addr.split("Branch:")[0].strip()
    comp_addr_p = Paragraph(comp_addr.replace("\n", "<br/>"), small_center)

    email_str = getattr(invoice, "company_email_snapshot", "") or "services@buildproreadymix.com"
    phone_str = getattr(invoice, "company_phone_snapshot", "") or "+91 7338391073, 9164728829"
    gstin_str = invoice.company_gstin_snapshot or "29DMVPS9392K1ZI"

    contact_p1 = Paragraph(f"<b>Email: {email_str}</b>", normal)
    contact_p2 = Paragraph(f"<b>Mob. No.: {phone_str}</b>", right_align)
    contact_p3 = Paragraph(f"<b>GST NO.: {gstin_str}</b>", ParagraphStyle("CenterBold", parent=normal, alignment=TA_CENTER, fontName="Helvetica-Bold"))

    banner_data = [
        [comp_title],
        [comp_addr_p],
        [Table([[contact_p1, contact_p2]], colWidths=[95 * mm, 95 * mm])],
        [contact_p3]
    ]
    banner_table = Table(banner_data, colWidths=[190 * mm])
    banner_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#bfdbfe")),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("LINEBELOW", (0, -1), (-1, -1), 1, colors.black),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(banner_table)

    # 4. Customer Details & Invoice Meta Block
    cust_name = invoice.customer_name_snapshot
    cust_addr = invoice.customer_address_snapshot or ""
    cust_gst = invoice.customer_gstin_snapshot or ""

    cust_info_cell = [
        Paragraph(f"<b>To, {cust_name}</b>", normal),
        Paragraph(f"<b>SITE: {cust_addr}</b>", normal),
        Paragraph(f"<b>GST: {cust_gst}</b>", normal)
    ]
    
    invoice_date_str = invoice.invoice_date.strftime("%d/%m/%Y")
    inv_info_cell = [
        Paragraph(f"<b>Invoice No.: <font color='red'>{invoice.invoice_number}</font></b>", normal),
        Paragraph(f"<b>Invoice Date: {invoice_date_str}</b>", normal),
        Paragraph("<b>Vehicle No: -</b>", normal)
    ]

    meta_grid = Table([[cust_info_cell, inv_info_cell]], colWidths=[115 * mm, 75 * mm])
    meta_grid.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEAFTER", (0, 0), (0, 0), 1, colors.black),
        ("LINEBELOW", (0, 0), (-1, -1), 1, colors.black),
        ("PADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(meta_grid)

    is_sqft_billing = getattr(invoice, "billing_type", "standard") == "construction_sqft"

    # 5. Product Line Items Grid (6 Columns: S.N., DESCRIPTION, HSN CODE, QTY/SQFT, RATE/SQFT, AMOUNT)
    header_row = [
        Paragraph("<b>S.N.</b>", small_center),
        Paragraph("<b>DESCRIPTION / WORK SCOPE</b>" if is_sqft_billing else "<b>D E S C R I P T I O N</b>", small_center),
        Paragraph("<b>SAC/HSN</b>" if is_sqft_billing else "<b>HSN CODE</b>", small_center),
        Paragraph("<b>SQFT</b>" if is_sqft_billing else "<b>QTY</b>", small_center),
        Paragraph("<b>RATE/SQFT (₹)</b>" if is_sqft_billing else "<b>RATE</b>", small_center),
        Paragraph("<b>AMOUNT (₹)</b>", small_center)
    ]
    
    rows = [header_row]
    for idx, item in enumerate(invoice.items, start=1):
        incl_rate = to_rupees(item.selling_price_paise)
        gst_rate = float(getattr(item, 'gst_rate', 0.0) or 0.0)
        
        if is_sqft_billing:
            if gst_rate > 0:
                excl_rate = incl_rate / (1.0 + (gst_rate / 100.0))
                excl_amt = excl_rate * float(item.quantity_bags)
            else:
                excl_rate = incl_rate
                excl_amt = incl_rate * float(item.quantity_bags)
        else:
            excl_rate = incl_rate / (1.0 + (gst_rate / 100.0))
            excl_amt = excl_rate * float(item.quantity_bags)

        rows.append([
            Paragraph(str(idx), small_center),
            Paragraph(item.product_name_snapshot, normal),
            Paragraph("9954" if is_sqft_billing else "3824", small_center),
            Paragraph(f"{item.quantity_bags:g}", small_center),
            Paragraph(f"{excl_rate:.2f}", right_align),
            Paragraph(f"{excl_amt:.2f}", right_align)
        ])

    while len(rows) < 5:
        rows.append(["", "", "", "", "", ""])

    col_w = [12 * mm, 85 * mm, 23 * mm, 20 * mm, 22 * mm, 28 * mm]

    # Combine items rows and summary rows into one seamless table so vertical grid lines align perfectly
    subtotal_val = to_rupees(invoice.subtotal_paise)
    transport_val = to_rupees(getattr(invoice, "transport_paise", 0) or 0)
    service_val = to_rupees(getattr(invoice, "service_charge_paise", 0) or 0)
    cgst_val = to_rupees(invoice.total_cgst_paise)
    sgst_val = to_rupees(invoice.total_sgst_paise)
    ro_val = to_rupees(invoice.round_off_paise)
    grand_val = to_rupees(invoice.grand_total_paise)

    summary_rows_count = 0

    if is_sqft_billing:
        summary_rows_count = 3
        rows.append([Paragraph("<b>Total Construction Value</b>", bold_right), "", "", "", "", Paragraph(f"<b>{subtotal_val:.2f}</b>", bold_right)])
        if sgst_val > 0 or cgst_val > 0:
            rows.append([Paragraph("<b>Add: SGST @ 9%</b>", bold_right), "", "", "", "", Paragraph(f"<b>{sgst_val:.2f}</b>", bold_right)])
            rows.append([Paragraph("<b>Add: CGST @ 9%</b>", bold_right), "", "", "", "", Paragraph(f"<b>{cgst_val:.2f}</b>", bold_right)])
            summary_rows_count += 2
        if transport_val > 0:
            rows.append([Paragraph("<b>Add: Extra Transport / Mobilization</b>", bold_right), "", "", "", "", Paragraph(f"<b>{transport_val:.2f}</b>", bold_right)])
            summary_rows_count += 1
        if service_val > 0:
            rows.append([Paragraph("<b>Add: Service Charge</b>", bold_right), "", "", "", "", Paragraph(f"<b>{service_val:.2f}</b>", bold_right)])
            summary_rows_count += 1
        rows.append([Paragraph("<b>Round Off (R/O)</b>", bold_right), "", "", "", "", Paragraph(f"<b>{ro_val:.2f}</b>", bold_right)])
        rows.append([Paragraph("<b>Net Payable Amount</b>", bold_right), "", "", "", "", Paragraph(f"<font size=11><b>{grand_val:.2f}</b></font>", bold_right)])
    else:
        summary_rows_count = 5
        rows.append([Paragraph("<b>Total Taxable Amount</b>", bold_right), "", "", "", "", Paragraph(f"<b>{subtotal_val:.2f}</b>", bold_right)])
        rows.append([Paragraph("<b>Add: SGST @ 9%</b>", bold_right), "", "", "", "", Paragraph(f"<b>{sgst_val:.2f}</b>", bold_right)])
        rows.append([Paragraph("<b>Add: CGST @ 9%</b>", bold_right), "", "", "", "", Paragraph(f"<b>{cgst_val:.2f}</b>", bold_right)])
        if transport_val > 0:
            rows.append([Paragraph("<b>Add: Transport Charges (Without GST)</b>", bold_right), "", "", "", "", Paragraph(f"<b>{transport_val:.2f}</b>", bold_right)])
            summary_rows_count += 1
        if service_val > 0:
            rows.append([Paragraph("<b>Add: Service Charge</b>", bold_right), "", "", "", "", Paragraph(f"<b>{service_val:.2f}</b>", bold_right)])
            summary_rows_count += 1
        rows.append([Paragraph("<b>Round Off (R/O)</b>", bold_right), "", "", "", "", Paragraph(f"<b>{ro_val:.2f}</b>", bold_right)])
        rows.append([Paragraph("<b>Grand Total Amount</b>", bold_right), "", "", "", "", Paragraph(f"<font size=11><b>{grand_val:.2f}</b></font>", bold_right)])

    items_table = Table(rows, colWidths=col_w)
    
    table_style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#bfdbfe")),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.75, colors.black),
        ("PADDING", (0, 0), (-1, -1), 4),
    ]

    for r_idx in range(-summary_rows_count, 0):
        table_style.append(("SPAN", (0, r_idx), (4, r_idx)))

    items_table.setStyle(TableStyle(table_style))
    story.append(items_table)
    story.append(Spacer(1, 4))

    # 7. Footer: Amount in words & Signatory
    amt_words = amount_in_words(invoice.grand_total_paise)
    words_p = Paragraph(f"<b>Amount in Words:</b> {amt_words}", normal)

    sign_path = resolve_image_path("sign.png") or resolve_image_path(invoice.signature_path_snapshot)
    stamp_img = _safe_image(invoice.stamp_path_snapshot, 22 * mm, 22 * mm)
    sig_img = _safe_image(sign_path, 28 * mm, 12 * mm)

    sign_elements = [
        Paragraph(f"<b>For {invoice.company_name_snapshot or 'BUILD PRO READY MIX'}</b>", right_align),
        Spacer(1, 4),
    ]

    if is_sealed:
        seal_overlaid = OverlaidSealSign(resolve_image_path("seal.png"), sign_path, width=32 * mm, height=32 * mm)
        seal_table = Table([[seal_overlaid]], colWidths=[75 * mm])
        seal_table.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        sign_elements.append(seal_table)
    else:
        # Unsigned invoice: Leave blank space above Authorised Signatory without sign.png
        sign_elements.append(Spacer(1, 20 * mm))

    sign_elements.append(Spacer(1, 2))
    sign_elements.append(Paragraph("<b>Authorised Signatory</b>", right_align))

    footer_table = Table([[words_p, sign_elements]], colWidths=[115 * mm, 75 * mm])
    footer_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("PADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(footer_table)

    doc.build(story)
    return output_path
