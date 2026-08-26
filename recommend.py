"""
recommend.py
-----------
Takes the ranked vendor list (the output of score_vendors) and asks
Gemini to explain, in plain language, why the top vendor is the best
choice -- naming the key tradeoff so a non-technical buyer understands
the reasoning, not just the ranking.

This is Step 4 of the AI Procurement Negotiation Agent.
"""

import google.generativeai as genai
import os

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-3.6-flash")


def generate_recommendation(ranked_vendors: list[dict]) -> str:
    """
    Input:  ranked_vendors -- the sorted list from score_vendors(),
            each vendor already has 'score' and 'score_breakdown'
    Output: a short, plain-language recommendation string
    """

    top_vendor = ranked_vendors[0]

    # We feed Claude/Gemini the ranked data (not raw quotes) --
    # this way it explains the SCORE, not just the raw numbers,
    # keeping its answer consistent with our own scoring logic
    # rather than re-deciding on its own.
    vendor_summary_lines = []
    for v in ranked_vendors:
        line = (
            f"- {v['vendor']}: price {v['price']} {v['currency']}, "
            f"delivery {v['delivery_days']} days, "
            f"payment terms '{v['payment_terms']}', "
            f"overall score {v['score']}/100 "
            f"(price_score={v['score_breakdown']['price_score']}, "
            f"delivery_score={v['score_breakdown']['delivery_score']}, "
            f"terms_score={v['score_breakdown']['terms_score']})"
        )
        vendor_summary_lines.append(line)

    vendor_summary = "\n".join(vendor_summary_lines)

    prompt = f"""You are a procurement assistant helping a small business
owner choose a vendor. Here is the ranked comparison, already scored
(higher is better, out of 100):

{vendor_summary}

Write a short recommendation (2-3 sentences) for a non-technical buyer:
1. State clearly which vendor to choose.
2. Name the ONE key tradeoff (e.g. it isn't the cheapest, but it has
   safer payment terms).
3. Keep it plain, confident, and free of jargon.

Do not restate every number -- explain the reasoning in plain words."""

    response = model.generate_content(prompt)
    return response.text.strip()


# ---- Quick test ----
if __name__ == "__main__":
    # Reuses the same 3-vendor ranked result you already got from
    # scoring.py, so we can test this step without re-running
    # everything from scratch.
    ranked_vendors = [
        {
            "vendor": "Vendor C",
            "price": 79000,
            "currency": "INR",
            "delivery_days": 12,
            "payment_terms": "Net 30",
            "score": 63.5,
            "score_breakdown": {"price_score": 46.2, "delivery_score": 50.0, "terms_score": 100},
        },
        {
            "vendor": "Vendor A",
            "price": 85000,
            "currency": "INR",
            "delivery_days": 10,
            "payment_terms": "50% advance, balance on delivery",
            "score": 48.0,
            "score_breakdown": {"price_score": 0.0, "delivery_score": 100.0, "terms_score": 60},
        },
        {
            "vendor": "Vendor B",
            "price": 72000,
            "currency": "INR",
            "delivery_days": 14,
            "payment_terms": "full payment upfront",
            "score": 46.0,
            "score_breakdown": {"price_score": 100.0, "delivery_score": 0.0, "terms_score": 20},
        },
    ]

    recommendation = generate_recommendation(ranked_vendors)
    print("AI Recommendation:")
    print(recommendation)
