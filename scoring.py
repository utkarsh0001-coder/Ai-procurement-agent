"""
scoring.py
-----------
Takes a list of extracted vendor quotes (the output of extract_quote,
one per vendor) and ranks them using a weighted score across price,
delivery speed, and payment terms.

This is Step 3 of the AI Procurement Negotiation Agent.
"""

# These weights decide how much each factor matters in the final score.
# They must add up to 1.0. Feel free to tweak these numbers --
# they're a genuine judgement call, and being able to justify them
# is a good thing to have ready for Q&A.
WEIGHTS = {
    "price": 0.4,          # cheaper is better
    "delivery_days": 0.3,  # faster is better
    "payment_terms": 0.3,  # less upfront cash risk is better
}


def _normalize_price(value, all_values):
    """
    Turns a raw price into a 0-100 score, where the CHEAPEST vendor
    gets 100 and the most expensive gets a lower score.

    Why we normalize: raw prices (like 85000 vs 72000) aren't
    directly comparable to raw delivery days (like 10 vs 14) --
    normalizing puts everything on the same 0-100 scale first.
    """
    lowest = min(all_values)
    highest = max(all_values)
    if highest == lowest:
        return 100  # everyone has the same price -- treat as tied
    # Cheaper price = higher score, so we flip the direction here.
    return 100 * (highest - value) / (highest - lowest)


def _normalize_delivery(value, all_values):
    """
    Same idea as price, but for delivery days -- FEWER days is better,
    so again the fastest vendor gets 100.
    """
    lowest = min(all_values)
    highest = max(all_values)
    if highest == lowest:
        return 100
    return 100 * (highest - value) / (highest - lowest)


def _score_payment_terms(payment_terms: str) -> float:
    """
    Payment terms are text, not numbers, so we can't "normalize" them
    the same way. Instead we use simple keyword rules to estimate how
    much cash-flow risk each term implies for the buyer.

    100 = safest for buyer (pay after delivery)
    0   = riskiest for buyer (pay everything upfront)

    This is a simplification -- a real version could ask Claude/Gemini
    to score this itself, but a clear rule-based version is easier to
    explain and defend in a demo.
    """
    text = payment_terms.lower()

    if "full" in text and ("advance" in text or "upfront" in text):
        return 20   # riskiest -- all cash paid before receiving anything
    if "50%" in text:
        return 60   # moderate -- half paid upfront
    if "net 30" in text or "net 60" in text or "after delivery" in text:
        return 100  # safest -- pay after receiving goods
    return 50  # unknown/unclear terms -- treat as medium risk


def score_vendors(quotes: list[dict]) -> list[dict]:
    """
    Input:  a list of extracted quote dictionaries (from extract_quote)
    Output: the same list, sorted best-to-worst, each with a
            "score" field added
    """

    prices = [q["price"] for q in quotes]
    deliveries = [q["delivery_days"] for q in quotes]

    for quote in quotes:
        price_score = _normalize_price(quote["price"], prices)
        delivery_score = _normalize_delivery(quote["delivery_days"], deliveries)
        terms_score = _score_payment_terms(quote["payment_terms"])

        # Combine the three scores using our weights.
        final_score = (
            price_score * WEIGHTS["price"]
            + delivery_score * WEIGHTS["delivery_days"]
            + terms_score * WEIGHTS["payment_terms"]
        )

        # Store the breakdown too -- useful for showing "why" later,
        # not just the final number.
        quote["score"] = round(final_score, 1)
        quote["score_breakdown"] = {
            "price_score": round(price_score, 1),
            "delivery_score": round(delivery_score, 1),
            "terms_score": round(terms_score, 1),
        }

    # Sort so the best (highest score) vendor comes first.
    ranked = sorted(quotes, key=lambda q: q["score"], reverse=True)
    return ranked


# ---- Quick test ----
if __name__ == "__main__":
    # These are the two quotes you already successfully extracted --
    # pasted here directly so we can test scoring without re-running
    # extraction every time.
    sample_quotes = [
        {
            "vendor": "Vendor A",
            "price": 79000,
            "currency": "INR",
            "quantity": 500,
            "delivery_days": 10,
            "payment_terms": "50% advance, balance on delivery",
            "conditions": "",
        },
        {
            "vendor": "Vendor B",
            "price": 72000,
            "currency": "INR",
            "quantity": 450,
            "delivery_days": 14,
            "payment_terms": "full payment upfront",
            "conditions": "",
        },
        {
            "vendor": "Vendor C",
            "price": 79000,
            "currency": "INR",
            "quantity": 500,
            "delivery_days": 12,
            "payment_terms": "Net 30",
            "conditions": "",
        },
    ]

    ranked_vendors = score_vendors(sample_quotes)

    print("Ranked vendors (best first):")
    for v in ranked_vendors:
        print(f"  {v['vendor']}: score={v['score']}  breakdown={v['score_breakdown']}")
