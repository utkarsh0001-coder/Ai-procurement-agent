"""
app.py
-----------
The dashboard -- this is the actual website a user opens. It ties
together everything built in Steps 2-5:

  upload quotes -> extract -> score -> recommend -> draft email -> approve

This is Step 6 of the AI Procurement Negotiation Agent.

Run this with:  streamlit run app.py
(NOT "python app.py" -- Streamlit needs its own command to work.)
"""

import streamlit as st
import pandas as pd
from pypdf import PdfReader

from extract_gemini import extract_quote
from scoring import score_vendors
from recommend import generate_recommendation
from negotiate import draft_negotiation_email
from po_generator import generate_po_pdf


def glass_box(text: str, kind: str = "info") -> None:
    """
    Renders a message in a glass-style box using OUR OWN html/css,
    instead of st.info/st.warning. Streamlit's built-in alert boxes
    are styled via internal class names that change between Streamlit
    versions, which is unreliable to target with custom CSS. This
    function sidesteps that entirely: we write the div and the class
    name ourselves, so the CSS in the theme block always matches,
    regardless of which Streamlit version is running.
    kind: "info", "warning", or "success" -- controls the left accent
    color and icon.
    """
    icon = {"info": "\u2139\ufe0f", "warning": "\u26a0\ufe0f", "success": "\u2705"}.get(kind, "\u2139\ufe0f")
    st.html(f'<div class="glass-box glass-{kind}">{icon}&nbsp;&nbsp;{text}</div>')


def read_uploaded_file(uploaded_file) -> str:
    """
    Turns an uploaded file (from Streamlit's file uploader) into
    plain text, whether it's a .txt file or a .pdf file.
    """
    if uploaded_file.name.lower().endswith(".pdf"):
        reader = PdfReader(uploaded_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text
    else:
        # .txt files (or anything plain-text) -- just decode the bytes.
        return uploaded_file.read().decode("utf-8", errors="ignore")


# ---------------- Page setup ----------------
st.set_page_config(page_title="AI Procurement Agent", layout="centered")

# ---------------- Animated background theme ----------------
# Premium top-to-bottom purple gradient (bright violet glow up top,
# fading through indigo into near-black at the bottom) with a
# drifting nebula glow layer, in the spirit of the reference mock.
# Uses an explicit fixed <div> layer (more reliable across Streamlit
# versions than a CSS pseudo-element, which some Streamlit themes
# can suppress).
st.html("""
<div id="animated-bg"></div>
<style>
/* Base gradient: bright violet at the top, sinking to near-black */
.stApp {
background: linear-gradient(180deg,
#4C2A85 0%,
#331E63 22%,
#221244 45%,
#150B2C 70%,
#0A0616 100%) !important;
background-attachment: fixed;
}

/* Explicit animated nebula/glow layer, fixed behind all content */
#animated-bg {
position: fixed;
top: -10%; left: -10%; right: -10%; bottom: -10%;
width: 120%; height: 120%;
background:
radial-gradient(ellipse 900px 550px at 20% 0%, rgba(196,181,253,0.28), transparent 60%),
radial-gradient(ellipse 750px 500px at 85% 10%, rgba(167,139,250,0.16), transparent 60%),
radial-gradient(ellipse 800px 650px at 50% 105%, rgba(76,42,133,0.55), transparent 65%);
filter: blur(55px);
animation: driftClouds 20s ease-in-out infinite alternate;
z-index: 0;
pointer-events: none;
}
@keyframes driftClouds {
0%   { transform: translate(0%, 0%) scale(1); }
50%  { transform: translate(3%, 4%) scale(1.08); }
100% { transform: translate(-3%, -2%) scale(1); }
}

/* Keep actual content above the animated layer */
.block-container, [data-testid="stHeader"], [data-testid="stToolbar"] {
position: relative;
z-index: 1;
}
[data-testid="stHeader"] { background: transparent !important; }

/* Light text, since the background is now dark */
h1, h2, h3, p, span, label, .stMarkdown, .stCaption { color: #F2EEFB !important; }
h1 { text-shadow: 0 0 24px rgba(167,139,250,0.35); }

/* Glass-style buttons to match the theme */
.stButton > button, .stDownloadButton > button {
background: rgba(255,255,255,0.08) !important;
color: #F2EEFB !important;
border: 1px solid rgba(196,181,253,0.30) !important;
border-radius: 10px !important;
backdrop-filter: blur(8px);
-webkit-backdrop-filter: blur(8px);
transition: all 0.2s ease;
}
.stButton > button:hover, .stDownloadButton > button:hover {
background: rgba(167,139,250,0.22) !important;
border: 1px solid #A78BFA !important;
box-shadow: 0 0 16px rgba(167,139,250,0.35);
}

/* Text areas / number inputs / text inputs -- glass look */
.stTextArea textarea, .stNumberInput input, .stTextInput input {
background: rgba(255,255,255,0.06) !important;
color: #F2EEFB !important;
border-radius: 10px !important;
border: 1px solid rgba(196,181,253,0.22) !important;
backdrop-filter: blur(6px);
-webkit-backdrop-filter: blur(6px);
}

/* ---- True glassmorphism for content "message" boxes ----
These target OUR OWN .glass-box class (rendered by the glass_box()
helper in app.py as raw HTML) instead of Streamlit's internal
data-testid names, which change between Streamlit versions and are
unreliable to target from custom CSS. Because we write both the div
and the CSS ourselves, this is guaranteed to match regardless of
Streamlit version. */
.glass-box {
background: rgba(255,255,255,0.08) !important;
border: 1px solid rgba(196,181,253,0.28) !important;
border-left: 4px solid rgba(196,181,253,0.55) !important;
border-radius: 14px !important;
padding: 14px 18px !important;
margin: 8px 0 !important;
backdrop-filter: blur(14px) saturate(140%);
-webkit-backdrop-filter: blur(14px) saturate(140%);
box-shadow: 0 4px 30px rgba(0,0,0,0.15);
color: #F2EEFB !important;
}
.glass-warning { border-left-color: #F5C563 !important; }
.glass-success { border-left-color: #7EE0A8 !important; }
.glass-info { border-left-color: #A78BFA !important; }

/* File uploader dropzone -- best-effort selectors since this one
still comes from Streamlit's own component, not our HTML */
[data-testid="stFileUploaderDropzone"],
[data-testid="stExpander"] {
background: rgba(255,255,255,0.07) !important;
border: 1px solid rgba(196,181,253,0.22) !important;
border-radius: 14px !important;
backdrop-filter: blur(14px) saturate(140%);
-webkit-backdrop-filter: blur(14px) saturate(140%);
}

[data-testid="stDataFrame"],
[data-testid="stDataFrameResizable"],
[data-testid="stElementContainer"]:has([data-testid="stDataFrame"]) {
background: rgba(255,255,255,0.05) !important;
border-radius: 14px !important;
border: 1px solid rgba(196,181,253,0.18) !important;
backdrop-filter: blur(10px);
-webkit-backdrop-filter: blur(10px);
overflow: hidden;
}

/* Fallback: Streamlit's legacy class-based markup (pre-testid era,
still shipped alongside data-testid in some versions) */
.stAlert, .element-container .stAlert {
background: rgba(255,255,255,0.07) !important;
border: 1px solid rgba(196,181,253,0.22) !important;
border-radius: 14px !important;
backdrop-filter: blur(14px) saturate(140%);
-webkit-backdrop-filter: blur(14px) saturate(140%);
}
</style>
""")

st.title("AI Procurement Agent")
st.write(
    "Upload 2-4 vendor quotes (PDF or text). "
    "The agent will extract, compare, and recommend a vendor -- "
    "then draft a negotiation email for you to review."
)

# ---------------- Step 1: Upload ----------------
uploaded_files = st.file_uploader(
    "Upload vendor quotes",
    type=["pdf", "txt"],
    accept_multiple_files=True,
)

if uploaded_files:

    # ---------------- Step 2: Extraction ----------------
    st.subheader("1. Extracted Quote Data")

    quotes = []
    for f in uploaded_files:
        raw_text = read_uploaded_file(f)
        extracted = extract_quote(raw_text)

        # Use the filename (without extension) as the vendor's name,
        # since quotes don't always state the vendor's name clearly.
        vendor_name = f.name.rsplit(".", 1)[0]
        extracted["vendor"] = vendor_name

        # If price is missing, this probably wasn't a real quote --
        # warn the user instead of silently including broken data.
        if extracted.get("price") is None:
            glass_box(
                f"Couldn't find price/quote details in '{f.name}'. "
                "Skipping this file -- please check it's a vendor quote.",
                kind="warning",
            )
            continue

        quotes.append(extracted)

    # Show the raw extracted table so the user can sanity-check the
    # AI's reading before it's used for scoring -- this is the human
    # review step for extraction, before we even reach scoring.
    if quotes:
        st.dataframe(pd.DataFrame(quotes))

    # ---------------- Step 3: Scoring ----------------
    if len(quotes) >= 2:
        st.subheader("2. Vendor Comparison & Scoring")
        ranked = score_vendors(quotes)
        st.dataframe(pd.DataFrame(ranked)[["vendor", "price", "delivery_days", "payment_terms", "score"]])

        top_vendor = ranked[0]

        # ---------------- Step 4: AI Recommendation ----------------
        st.subheader("3. AI Recommendation")
        with st.spinner("Generating recommendation..."):
            recommendation = generate_recommendation(ranked)
        glass_box(recommendation, kind="info")

        # ---------------- Step 5: Negotiation Email ----------------
        st.subheader("4. Negotiation Email Draft")
        with st.spinner("Drafting negotiation email..."):
            email_draft = draft_negotiation_email(
                top_vendor, num_competing_offers=len(ranked) - 1
            )

        # This is the editable text box -- the human review/approval
        # step made real. The user can change anything here before
        # using it.
        edited_email = st.text_area(
            "Edit before sending:",
            value=email_draft,
            height=220,
        )

        if st.button("Approve Email"):
            st.success(
                "Approved. Copy the text above and send it to "
                f"{top_vendor['vendor']}."
            )

        # ---------------- Step 5.5: Purchase Order ----------------
        st.subheader("5. Generate Purchase Order")
        st.write(
            "Once the vendor confirms final terms over email (which may "
            "differ from the original quote if they negotiated), enter "
            "the agreed price below and generate the PO."
        )

        buyer_name = st.text_input("Your company name", value="Your Company Name")

        # Pre-filled with the original quoted price -- but editable,
        # since the actual final price only exists in a real email
        # reply from the vendor. We never guess this ourselves.
        final_price = st.number_input(
            "Final agreed price (edit if the vendor negotiated a different price)",
            value=float(top_vendor["price"]),
            step=100.0,
        )

        if st.button("Generate Purchase Order"):
            po_bytes = generate_po_pdf(
                top_vendor, buyer_name=buyer_name, final_price=final_price
            )
            st.download_button(
                label="Download Purchase Order (PDF)",
                data=po_bytes,
                file_name=f"PO_{top_vendor['vendor']}.pdf",
                mime="application/pdf",
            )
            st.success("Purchase order generated -- click above to download.")

    elif len(quotes) == 1:
        glass_box("Upload at least 2 valid vendor quotes to compare and score them.", kind="warning")

else:
    st.write("Waiting for quotes to be uploaded.")
