"""
SIH26100 — Authentic Demo Document Generator
Generates realistic PDF documents for all 12 bidders:
- Form GST REG-06 (GST Registration Certificate)
- Corporate PAN Card
- Audited Financial Statements with UDIN
- Udyam MSME Registration Certificate
- OEM Authorization Letter (MAF)
- Make in India (MII) Self-Declaration

Outputs to:
- data/documents/
- backend/data/documents/
"""
import os
import sys
import json
import hashlib
import random
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# Add parent directory to path so we can import synthetic_data
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from mock_apis.synthetic_data import get_all_bidders, SAMPLE_TENDER

OUTPUT_DIRS = [
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/documents")),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../data/documents")),
]

for d in OUTPUT_DIRS:
    os.makedirs(d, exist_ok=True)


def _get_styles():
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        alignment=1,
        textColor=colors.HexColor("#0f172a"),
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        alignment=1,
        textColor=colors.HexColor("#475569"),
    )
    header_style = ParagraphStyle(
        "SectionHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#1e293b"),
    )
    body_style = ParagraphStyle(
        "DocBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#334155"),
    )
    bold_style = ParagraphStyle(
        "DocBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#0f172a"),
    )
    mono_style = ParagraphStyle(
        "DocMono",
        parent=styles["Normal"],
        fontName="Courier-Bold",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#0284c7"),
    )
    return {
        "title": title_style,
        "subtitle": subtitle_style,
        "header": header_style,
        "body": body_style,
        "bold": bold_style,
        "mono": mono_style,
    }


def _save_pdf_to_all(filename: str, story: list) -> str:
    primary_path = os.path.join(OUTPUT_DIRS[0], filename)
    doc = SimpleDocTemplate(
        primary_path,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )
    doc.build(story)

    # Copy to secondary output dir
    secondary_path = os.path.join(OUTPUT_DIRS[1], filename)
    with open(primary_path, "rb") as src, open(secondary_path, "wb") as dst:
        dst.write(src.read())

    return primary_path


def generate_gst_certificate(bidder: dict) -> str:
    """Generate Form GST REG-06 Registration Certificate."""
    st = _get_styles()
    story = []

    # Header
    story.append(Paragraph("GOVERNMENT OF INDIA", st["title"]))
    story.append(Paragraph("GOODS AND SERVICES TAX DEPARTMENT", st["subtitle"]))
    story.append(Spacer(1, 8))
    story.append(Paragraph("<b>Form GST REG-06</b>", st["title"]))
    story.append(Paragraph("<i>[See Rule 10(1)]</i><br/><b>REGISTRATION CERTIFICATE</b>", st["subtitle"]))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0f172a"), spaceAfter=15))

    addr = bidder.get("registered_address", {})
    addr_str = f"{addr.get('line1', '')}, {addr.get('line2', '')}, {addr.get('city', '')}, {addr.get('state', '')} - {addr.get('pincode', '')}"

    data = [
        [Paragraph("Registration Number (GSTIN):", st["bold"]), Paragraph(bidder.get("gstin", "N/A"), st["mono"])],
        [Paragraph("Legal Name:", st["bold"]), Paragraph(bidder.get("entity_name", "N/A"), st["body"])],
        [Paragraph("Trade Name:", st["bold"]), Paragraph(bidder.get("trade_name") or bidder.get("entity_name", "N/A"), st["body"])],
        [Paragraph("Constitution of Business:", st["bold"]), Paragraph(bidder.get("entity_type", "Private Limited Company"), st["body"])],
        [Paragraph("Address of Principal Place of Business:", st["bold"]), Paragraph(addr_str, st["body"])],
        [Paragraph("Date of Liability:", st["bold"]), Paragraph(bidder.get("gst_registration_date", "2018-07-01"), st["body"])],
        [Paragraph("Period of Validity:", st["bold"]), Paragraph(f"From {bidder.get('gst_registration_date', '2018-07-01')} To: Regular", st["body"])],
        [Paragraph("Type of Registration:", st["bold"]), Paragraph("Regular Taxpayer", st["body"])],
        [Paragraph("Registration Status:", st["bold"]), Paragraph(bidder.get("gst_status", "Active"), st["bold"])],
    ]

    table = Table(data, colWidths=[200, 330])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("PADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(table)
    story.append(Spacer(1, 15))

    # Verification footer
    story.append(Paragraph("<b>Details of Approving Authority:</b>", st["header"]))
    story.append(Paragraph("Jurisdictional Officer: Assistant Commissioner of State Tax, Ward 4.<br/>This is a system-generated certificate based on statutory filing.", st["body"]))
    story.append(Spacer(1, 15))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#94a3b8"), spaceAfter=5))
    story.append(Paragraph(f"Digital Verification Checksum: {hashlib.sha256(f'{bidder['gstin']}_REG06_OFFICIAL'.encode()).hexdigest()}", st["subtitle"]))

    filename = f"DOC-GST-{bidder['bidder_id']}.pdf"
    return _save_pdf_to_all(filename, story)


def generate_pan_card(bidder: dict) -> str:
    """Generate Corporate PAN Card."""
    st = _get_styles()
    story = []

    story.append(Paragraph("INCOME TAX DEPARTMENT", st["title"]))
    story.append(Paragraph("GOVERNMENT OF INDIA", st["subtitle"]))
    story.append(Spacer(1, 8))
    story.append(Paragraph("<b>PERMANENT ACCOUNT NUMBER CARD</b>", st["title"]))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#1e3a8a"), spaceAfter=15))

    pan_name = bidder.get("pan_registered_name", bidder["entity_name"])
    data = [
        [Paragraph("Permanent Account Number (PAN):", st["bold"]), Paragraph(bidder.get("pan", "N/A"), st["mono"])],
        [Paragraph("Name of Entity:", st["bold"]), Paragraph(pan_name, st["body"])],
        [Paragraph("Entity Type:", st["bold"]), Paragraph(bidder.get("entity_type", "Company"), st["body"])],
        [Paragraph("Date of Incorporation:", st["bold"]), Paragraph(bidder.get("incorporation_date", "2018-03-15"), st["body"])],
        [Paragraph("Tax Deduction Account No (TAN):", st["bold"]), Paragraph(f"DEL{bidder.get('pan', 'AABCT1234')[:4]}123E", st["body"])],
    ]

    table = Table(data, colWidths=[200, 330])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f0fdf4")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#86efac")),
        ("PADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(table)
    story.append(Spacer(1, 20))
    story.append(Paragraph("This card is proof of identification issued under Section 139A of the Income Tax Act, 1961.", st["subtitle"]))

    filename = f"DOC-PAN-{bidder['bidder_id']}.pdf"
    return _save_pdf_to_all(filename, story)


def generate_balance_sheet(bidder: dict) -> str:
    """Generate Audited Financial Statements with UDIN."""
    st = _get_styles()
    story = []

    story.append(Paragraph(f"INDEPENDENT AUDITOR'S REPORT & FINANCIAL STATEMENTS", st["title"]))
    story.append(Paragraph(f"Entity: {bidder['entity_name']}", st["subtitle"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph("Statutory Audit for Financial Years 2023-24, 2024-25, 2025-26", st["subtitle"]))
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0f172a"), spaceAfter=12))

    # UDIN block (B007 has flagged/invalid UDIN)
    bidder_id = bidder["bidder_id"]
    if bidder_id == "B007":
        udin_text = "UDIN: NOT_GENERATED (Unregistered / Shell Entity — Audit Incomplete)"
        udin_color = colors.HexColor("#dc2626")
    else:
        udin_text = f"ICAI UDIN: 24{random.randint(100000, 999999)}AB{random.randint(1000, 9999)} (Verified with ICAI Portal)"
        udin_color = colors.HexColor("#16a34a")

    udin_style = ParagraphStyle(
        "UDINStyle",
        parent=st["bold"],
        textColor=udin_color,
    )
    story.append(Paragraph(f"<b>Statutory Compliance:</b> {udin_text}", udin_style))
    story.append(Paragraph("Statutory Auditors: M/s Singhal & Associates, Chartered Accountants (FRN: 014285N)", st["body"]))
    story.append(Spacer(1, 10))

    # Financial Turnover Table
    turnovers = bidder.get("annual_turnover", [])
    table_data = [
        [
            Paragraph("<b>Financial Year</b>", st["bold"]),
            Paragraph("<b>Gross Annual Turnover (INR)</b>", st["bold"]),
            Paragraph("<b>Net Worth (INR)</b>", st["bold"]),
            Paragraph("<b>Profit After Tax (INR)</b>", st["bold"]),
        ]
    ]

    for t in turnovers:
        amt = t.get("amount", 0)
        net_worth = int(amt * 0.45)
        pat = int(amt * 0.08)
        table_data.append([
            Paragraph(t.get("fy", "FY"), st["body"]),
            Paragraph(f"INR {amt:,.2f}", st["mono"]),
            Paragraph(f"INR {net_worth:,.2f}", st["body"]),
            Paragraph(f"INR {pat:,.2f}", st["body"]),
        ])

    avg_turnover = sum(t.get("amount", 0) for t in turnovers) // max(len(turnovers), 1) if turnovers else 0
    table_data.append([
        Paragraph("<b>Average 3-Year Turnover:</b>", st["bold"]),
        Paragraph(f"<b>INR {avg_turnover:,.2f}</b>", st["mono"]),
        Paragraph("<b>Compliant</b>", st["bold"]),
        Paragraph("-", st["body"]),
    ])

    fin_table = Table(table_data, colWidths=[120, 150, 130, 130])
    fin_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("PADDING", (0, 0), (-1, -1), 6),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.HexColor("#ffffff"), colors.HexColor("#f8fafc")]),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#f1f5f9")),
    ]))
    story.append(fin_table)
    story.append(Spacer(1, 15))

    story.append(Paragraph("<b>Auditor's Opinion:</b>", st["header"]))
    if bidder_id == "B007":
        story.append(Paragraph(
            "DISCLAIMER OF OPINION: We were unable to obtain sufficient appropriate audit evidence to provide a basis for an audit opinion. "
            "The entity has no active operational premises, negligible asset records, and failure of statutory verification.",
            st["body"],
        ))
    else:
        story.append(Paragraph(
            "In our opinion and to the best of our information and according to explanations given to us, the aforesaid financial statements "
            "give a true and fair view in conformity with the accounting principles generally accepted in India.",
            st["body"],
        ))

    filename = f"DOC-AUDIT-{bidder['bidder_id']}.pdf"
    return _save_pdf_to_all(filename, story)


def generate_udyam_certificate(bidder: dict) -> str:
    """Generate Udyam MSME Registration Certificate."""
    st = _get_styles()
    story = []

    story.append(Paragraph("MINISTRY OF MICRO, SMALL & MEDIUM ENTERPRISES", st["title"]))
    story.append(Paragraph("GOVERNMENT OF INDIA", st["subtitle"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph("<b>UDYAM REGISTRATION CERTIFICATE</b>", st["title"]))
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0f172a"), spaceAfter=12))

    udyam_no = bidder.get("udyam_no") or "NOT APPLICABLE (Non-MSME)"
    category = bidder.get("msme_category") or "Not Applicable"
    validity = bidder.get("msme_valid_until") or "N/A"

    data = [
        [Paragraph("Udyam Registration Number:", st["bold"]), Paragraph(udyam_no, st["mono"])],
        [Paragraph("Name of Enterprise:", st["bold"]), Paragraph(bidder["entity_name"], st["body"])],
        [Paragraph("Type of Enterprise:", st["bold"]), Paragraph(category, st["bold"])],
        [Paragraph("Major Activity:", st["bold"]), Paragraph("Manufacturing / Services (IT Equipment & Services)", st["body"])],
        [Paragraph("Date of Commencement of Production:", st["bold"]), Paragraph(bidder.get("incorporation_date", "2018-03-15"), st["body"])],
        [Paragraph("Valid Until:", st["bold"]), Paragraph(validity, st["body"])],
        [Paragraph("National Industry Classification (NIC) Code:", st["bold"]), Paragraph("2620 - Manufacture of computers and peripheral equipment", st["body"])],
    ]

    table = Table(data, colWidths=[200, 330])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fef3c7")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#fcd34d")),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(table)
    story.append(Spacer(1, 15))
    story.append(Paragraph("This certificate is issued under Section 7 of the MSMED Act, 2006 for public procurement preference.", st["subtitle"]))

    filename = f"DOC-MSME-{bidder['bidder_id']}.pdf"
    return _save_pdf_to_all(filename, story)


def generate_oem_auth(bidder: dict) -> str:
    """Generate Manufacturer Authorization Form (MAF)."""
    st = _get_styles()
    story = []

    oem_name = bidder.get("oem_name", "Authorized Hardware OEM")
    story.append(Paragraph(f"{oem_name.upper()} — GLOBAL ENTERPRISE SOLUTIONS", st["title"]))
    story.append(Paragraph("MANUFACTURER'S AUTHORIZATION FORM (MAF)", st["subtitle"]))
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#1e3a8a"), spaceAfter=12))

    story.append(Paragraph("<b>To:</b> The Procurement Officer, Government e-Marketplace (GeM)<br/>"
                           f"<b>Tender Ref:</b> {SAMPLE_TENDER['tender_id']}<br/>"
                           f"<b>Subject:</b> Manufacturer Authorization for {SAMPLE_TENDER['title']}", st["body"]))
    story.append(Spacer(1, 10))

    body_letter = (
        f"Dear Sir/Madam,<br/><br/>"
        f"We, <b>{oem_name}</b>, who are established and reputable manufacturers of Desktop Computers having factories at "
        f"Industrial Zone, Electronic City, do hereby authorize <b>{bidder['entity_name']}</b> "
        f"(GSTIN: {bidder.get('gstin', '')}) to submit a bid, negotiate and conclude the contract with you against the above tender.<br/><br/>"
        f"We hereby extend our full <b>3-Year Comprehensive On-Site Manufacturer Warranty</b> and technical support "
        f"for the 500 Desktop Computers offered for supply by the aforesaid bidder.<br/><br/>"
        f"<b>Authorization Validity:</b> Valid throughout the entire tender execution and warranty period."
    )
    story.append(Paragraph(body_letter, st["body"]))
    story.append(Spacer(1, 20))

    sig_data = [
        [Paragraph(f"<b>For {oem_name}</b><br/>Authorized Signatory: Global Channels Lead<br/>Seal & Signature", st["body"])],
    ]
    sig_table = Table(sig_data, colWidths=[300])
    sig_table.setStyle(TableStyle([
        ("LINEBEFORE", (0, 0), (-1, -1), 2, colors.HexColor("#2563eb")),
        ("PADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(sig_table)

    filename = f"DOC-OEM-{bidder['bidder_id']}.pdf"
    return _save_pdf_to_all(filename, story)


def generate_mii_declaration(bidder: dict) -> str:
    """Generate Make in India (MII) Local Value Addition Self-Declaration."""
    st = _get_styles()
    story = []

    story.append(Paragraph(bidder["entity_name"].upper(), st["title"]))
    story.append(Paragraph("LOCAL VALUE ADDITION / MAKE IN INDIA SELF-DECLARATION", st["subtitle"]))
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0f172a"), spaceAfter=12))

    mii_pct = bidder.get("make_in_india_percent", 50)
    body_text = (
        f"In accordance with the Public Procurement (Preference to Make in India) Order 2017 (DPIIT Order No. P-45021/2/2017-PP(BE-II)), "
        f"we hereby certify that the products offered by <b>{bidder['entity_name']}</b> against Tender "
        f"<b>{SAMPLE_TENDER['tender_id']}</b> contain:<br/><br/>"
        f"<font size=12 color='#0284c7'><b>Local Domestic Value Addition: {mii_pct}%</b></font><br/><br/>"
        f"<b>Classification:</b> {'Class-I Local Supplier (>= 50%)' if mii_pct >= 50 else 'Class-II Local Supplier (>= 20% to < 50%)'}<br/>"
        f"<b>Location of Local Value Addition:</b> Manufacturing Facility, Industrial Area, Sector 18, Gurugram, India.<br/><br/>"
        f"We understand that false declarations violate the Code of Integrity under Rule 175(1)(i)(h) of the General Financial Rules (GFR-2017) "
        f"and shall attract debarment up to two years."
    )
    story.append(Paragraph(body_text, st["body"]))
    story.append(Spacer(1, 20))

    directors = bidder.get("directors", [])
    dir_name = directors[0]["name"] if directors else "Managing Director"
    story.append(Paragraph(f"<b>Authorized Signatory:</b> {dir_name}<br/>DIN: {directors[0].get('din', 'N/A') if directors else 'N/A'}", st["body"]))

    filename = f"DOC-MII-{bidder['bidder_id']}.pdf"
    return _save_pdf_to_all(filename, story)


def main():
    bidders = get_all_bidders()
    print(f"Generating authentic PDF documents for {len(bidders)} bidders...")

    manifest = {}
    for b in bidders:
        b_id = b["bidder_id"]
        manifest[b_id] = {
            "gst": generate_gst_certificate(b),
            "pan": generate_pan_card(b),
            "audit": generate_balance_sheet(b),
            "udyam": generate_udyam_certificate(b),
            "oem": generate_oem_auth(b),
            "mii": generate_mii_declaration(b),
        }
        print(f"  [OK] Generated 6 documents for {b_id} ({b['entity_name']})")

    manifest_path = os.path.join(OUTPUT_DIRS[0], "documents_manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"Successfully generated {len(bidders) * 6} PDF documents!")
    print(f"Manifest saved to: {manifest_path}")


if __name__ == "__main__":
    main()
