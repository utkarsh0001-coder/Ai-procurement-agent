"""
negotiate.py
-----------
Takes the top-ranked vendor and drafts a polite, professional
negotiation email requesting better price or terms -- referencing
that competing offers were considered, without naming them directly
(keeps things professional, doesn't reveal competitor pricing).

This is Step 5 of the AI Procurement Negotiation Agent -- the
key differentiator from plain comparison tools: the agent doesn't
just recommend, it drafts the next ACTION for the buyer to take.

IMPORTANT: this only ever produces a DRAFT. Nothing is sent
automatically -- the human reviews and approves before anything
goes to a real vendor. This matches the human-approval step in
our architecture.
"""

import google.generativeai as genai
import os

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-3.6-flash")


def draft_negotiation_email(top_vendor: dict, num_competing_offers: int) -> str:
    """
    Input:  top_vendor -- the single best-scored vendor dict
            num_competing_offers -- how many other quotes were compared
            (used to say "we're evaluating other offers" honestly,
            without exposing competitor names or prices)
    Output: a ready-to-edit email draft as a string
    """

    prompt = f"""Write a short, polite, professional negotiation email
to a vendor, on behalf of a small business buyer.

Context (for you only, do not repeat these numbers directly in the
email unless naturally relevant):
- Vendor: {top_vendor['vendor']}
- Their quoted price: {top_vendor['price']} {top_vendor['currency']}
- Delivery time: {top_vendor['delivery_days']} days
- Payment terms offered: {top_vendor['payment_terms']}
- We are also considering {num_competing_offers} other vendor offers
  in a similar range (do not name them or give their prices).

The email should:
1. Thank them for the quote.
2. Mention we're evaluating a few offers in a similar range, to
   create gentle leverage -- without sounding aggressive or revealing
   competitor details.
3. Politely ask if they can improve the price OR offer more flexible
   payment terms.
4. Keep it under 100 words, professional and friendly in tone.
5. Sign off generically as "Procurement Team" (no fake personal name).

Return ONLY the email text, no subject line, no extra commentary."""

    response = model.generate_content(prompt)
    return response.text.strip()


# ---- Quick test ----
if __name__ == "__main__":
    # The winning vendor from your real scoring.py test run.
    top_vendor = {
        "vendor": "Vendor C",
        "price": 79000,
        "currency": "INR",
        "delivery_days": 12,
        "payment_terms": "Net 30",
        "score": 63.5,
    }

    email_draft = draft_negotiation_email(top_vendor, num_competing_offers=2)
    print("Negotiation Email Draft:")
    print(email_draft)
