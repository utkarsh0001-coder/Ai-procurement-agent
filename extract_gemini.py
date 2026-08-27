"""
extract.py  (Gemini version)
-----------
Takes raw vendor quote text (from a PDF, email, or scanned sheet)
and asks Gemini to pull out structured data: price, delivery time,
payment terms, and any special conditions.

This is a drop-in replacement for the Claude version, using Google's
free-tier Gemini API instead -- no international card needed.

Once your Claude API payment goes through, you can swap this back by
changing only the "API CALL" section below -- the prompt, JSON
parsing, and function shape all stay the same.
"""

import google.generativeai as genai
import json
import os

# Reads your GEMINI_API_KEY environment variable automatically.
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

# Gemini 3.6 Flash: fast, free-tier friendly, good enough for this task.
model = genai.GenerativeModel("gemini-3.6-flash")


def extract_quote(quote_text: str) -> dict:
    """
    Sends raw quote text to Gemini and gets back structured data.

    Input:  a messy block of text (copied from a PDF, email, etc.)
    Output: a Python dictionary with clean fields
    """

    # Same prompt logic as the Claude version -- being specific about
    # the exact JSON fields is what makes the output reliable.
    prompt = f"""You are extracting structured data from a vendor quote.

Read the quote below and return ONLY a JSON object (no other text,
no markdown code fences) with these exact fields:
- price (number, the TOTAL price for the full order, no currency symbol)
- currency (e.g. "INR", "USD")
- quantity (number, if mentioned, else null)
- delivery_days (number of days until delivery, if mentioned, else null)
- payment_terms (short string capturing the FULL payment structure,
  e.g. "50% advance, balance on delivery", "30% advance + 2 installments
  at 15/30 days", "60-day credit terms")
- conditions (short string summarizing any other conditions, or "" if none)

IMPORTANT rules for tricky quotes:
1. If the quote gives a PER-UNIT or PER-PIECE rate (e.g. "Rs 197 per unit")
   instead of a total, you MUST calculate the total yourself:
   total_price = unit_price x quantity. Return that calculated TOTAL as
   "price", never the per-unit rate alone.
2. If delivery is given as a RANGE (e.g. "18-20 days" or "usually 15 days,
   worst case 4 weeks"), use the WORST-CASE (longest/latest) number for
   "delivery_days", since that is the safer number for planning purposes.
   Convert weeks to days (1 week = 7 days) if needed.
3. If a discount is conditional (e.g. "3% off if paid within 15 days"),
   report the STANDARD/default price as "price", and mention the
   conditional discount in "conditions" instead.

Quote:
{quote_text}

Return ONLY the JSON object, nothing else."""

    # ---- API CALL (this is the part that changes if you swap providers) ----
    response = model.generate_content(prompt)
    raw_text = response.text
    # --------------------------------------------------------------------

    # Gemini sometimes wraps JSON in ```json ... ``` markdown fences --
    # this cleans that up before parsing, since Claude doesn't usually
    # do this but Gemini occasionally does.
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned.replace("json", "", 1).strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        print("Could not parse Gemini's response as JSON:")
        print(raw_text)
        data = None

    return data


# ---- Quick test ----
if __name__ == "__main__":
    sample_quote = """
    Dear Sir, thank you for your interest. We quote INR 85,000 for
    500 packaging boxes. Delivery within 10 working days.
    Payment: 50% advance, balance on delivery.
    """

    result = extract_quote(sample_quote)
    print("Extracted data:")
    print(result)