"""
po_generator.py
-----------
Generates a formatted Purchase Order (PO) as a downloadable PDF,
auto-filled with the approved vendor's details.

This is an ADDITIONAL feature beyond the core 5-step pipeline --
it's what a plain chatbot answer can't do: produce a real,
professional business DOCUMENT as output, not just text in a
chat bubble.

Note: this generates a PO DOCUMENT only -- it does not integrate
with real accounting/inventory systems. That's intentionally left
as future scope (see Section 5, Scalability, in the proposal).
"""

from fpdf import FPDF
from datetime import date
import random


def generate_po_number() -> str:
    """
    Creates a simple, unique-looking PO number, e.g. "PO-20260825-4821".
    Uses today's date plus a random 4-digit number so POs don't collide.
    In a real system, this would come from a proper sequential counter
    stored in a database -- this is a reasonable stand-in for a demo.
    """
    today_str = date.today().strftime("%Y%m%d")
    random_suffix = random.randint(1000, 9999)
    return f"PO-{today_str}-{random_suffix}"


def generate_po_pdf(vendor: dict, buyer_name: str = "Your Company Name", final_price: float = None) -> bytes:
    """
    Input:  vendor -- the approved vendor's dict (price, delivery_days,
            payment_terms, vendor name, etc.)
            buyer_name -- your company's name, shown on the PO
            final_price -- the ACTUAL agreed price after negotiation,
            entered by the human. If the vendor didn't negotiate,
            this can be left as None, and we just use the original
            quoted price instead.
    Output: the finished PDF, as raw bytes (ready to offer as a download
            in the Streamlit dashboard)
    """

    po_number = generate_po_number()
    today = date.today().strftime("%d %B %Y")

    # If no negotiated price was entered, fall back to the original
    # quote. We NEVER guess a negotiated price ourselves -- it only
    # ever comes from a human confirming what the vendor actually
    # agreed to over real email.
    quoted_price = vendor["price"]
    agreed_price = final_price if final_price is not None else quoted_price
    was_negotiated = agreed_price != quoted_price

    pdf = FPDF()
    pdf.add_page()

    # ---- Header ----
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 12, "PURCHASE ORDER", ln=True)

    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, f"PO Number: {po_number}", ln=True)
    pdf.cell(0, 8, f"Date: {today}", ln=True)
    pdf.ln(6)

    # ---- Buyer / Vendor details ----
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Buyer:", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, buyer_name, ln=True)
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Vendor:", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, vendor["vendor"], ln=True)
    pdf.ln(6)

    # ---- Order details table ----
    pdf.set_font("Helvetica", "B", 11)
    col_widths = [70, 40, 40, 40]
    headers = ["Item", "Quantity", "Unit", "Total Price"]
    for w, h in zip(col_widths, headers):
        pdf.cell(w, 9, h, border=1)
    pdf.ln()

    pdf.set_font("Helvetica", "", 11)
    quantity = vendor.get("quantity") or "-"
    row = [
        "Goods as per quotation",
        str(quantity),
        vendor.get("currency", ""),
        f"{agreed_price} {vendor.get('currency', '')}",
    ]
    for w, val in zip(col_widths, row):
        pdf.cell(w, 9, str(val), border=1)
    pdf.ln(8)

    # If the final price differs from the original quote, show both --
    # full transparency on what changed through negotiation.
    if was_negotiated:
        pdf.set_font("Helvetica", "I", 10)
        pdf.cell(
            0, 7,
            f"Note: Original quoted price was {quoted_price} {vendor.get('currency', '')}; "
            f"final price reflects negotiated terms.",
            ln=True,
        )
        pdf.ln(4)
    else:
        pdf.ln(4)

    # ---- Terms ----
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Terms", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, f"Delivery: within {vendor.get('delivery_days', '-')} days", ln=True)
    pdf.cell(0, 7, f"Payment terms: {vendor.get('payment_terms', '-')}", ln=True)
    pdf.ln(10)

    # ---- Footer note ----
    pdf.set_font("Helvetica", "I", 9)
    pdf.multi_cell(
        0, 6,
        "This purchase order was generated based on an AI-assisted vendor "
        "comparison and reviewed/approved by the buyer before issuance."
    )

    # fpdf2 can output directly as bytes, ready for a download button.
    return bytes(pdf.output())


# ---- Quick test ----
if __name__ == "__main__":
    top_vendor = {
        "vendor": "Vendor C",
        "price": 79000,
        "currency": "INR",
        "quantity": 500,
        "delivery_days": 12,
        "payment_terms": "Net 30",
    }

    # Test 1: no negotiation -- uses original quoted price
    pdf_bytes = generate_po_pdf(top_vendor, buyer_name="ABC Furniture Pvt Ltd")
    with open("test_purchase_order.pdf", "wb") as f:
        f.write(pdf_bytes)
    print("PO generated (no negotiation): test_purchase_order.pdf")

    # Test 2: vendor agreed to a lower price after negotiation
    pdf_bytes_negotiated = generate_po_pdf(
        top_vendor, buyer_name="ABC Furniture Pvt Ltd", final_price=75000
    )
    with open("test_purchase_order_negotiated.pdf", "wb") as f:
        f.write(pdf_bytes_negotiated)
    print("PO generated (negotiated price): test_purchase_order_negotiated.pdf")
