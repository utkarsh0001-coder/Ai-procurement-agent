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
- price (number, just the number, no currency symbol)
- currency (e.g. "INR", "USD")
- quantity (number, if mentioned, else null)
- delivery_days (number of days until delivery, if mentioned, else null)
- payment_terms (short string, e.g. "50% advance", "Net 30")
- conditions (short string summarizing any other conditions, or "" if none)

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
Chapter 4: The History of Renaissance Art
The Renaissance period, spanning roughly the 14th to 17th century...
"""


    result = extract_quote(sample_quote)
    print("Extracted data:")
    print(result)
