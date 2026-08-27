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
# Dark navy backdrop with slow-drifting soft "cloud" glows, like light
# breaking through atmosphere into deep blue. Pure CSS -- no images,
# no external assets, works entirely inside Streamlit's markdown.
st.markdown("""
<style>
/* Base dark navy gradient across the whole app */
.stApp {
    background: radial-gradient(ellipse at top left, #16324f 0%, #0b1f3a 45%, #060f1f 100%);
    background-attachment: fixed;
}

/* The drifting "cloud break" layer -- soft blurred glows that slowly move */
.stApp::before {
    content: "";
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background:
        radial-gradient(ellipse 900px 550px at 15% -10%, rgba(255,255,255,0.14), transparent 60%),
        radial-gradient(ellipse 700px 450px at 90% 5%, rgba(143,211,238,0.10), transparent 60%),
        radial-gradient(ellipse 800px 600px at 50% 105%, rgba(19,117,145,0.35), transparent 65%);
    filter: blur(45px);
    animation: driftClouds 22s ease-in-out infinite alternate;
    z-index: 0;
    pointer-events: none;
}
@keyframes driftClouds {
    0%   { transform: translate(0%, 0%) scale(1); }
    50%  { transform: translate(3%, 2%) scale(1.06); }
    100% { transform: translate(-3%, -2%) scale(1); }
}

/* Keep actual content above the animated layer */
.block-container { position: relative; z-index: 1; }

/* Light text, since the background is now dark */
h1, h2, h3, p, span, label, .stMarkdown, .stCaption { color: #EAF1F8 !important; }

/* Glass-style buttons to match the theme */
.stButton > button, .stDownloadButton > button {
    background: rgba(255,255,255,0.10) !important;
    color: #EAF1F8 !important;
    border: 1px solid rgba(255,255,255,0.25) !important;
    border-radius: 10px !important;
    backdrop-filter: blur(6px);
}
.stButton > button:hover, .stDownloadButton > button:hover {
    background: rgba(201,162,39,0.25) !important;
    border: 1px solid #C9A227 !important;
}

/* Text areas / number inputs / text inputs -- glass look */
.stTextArea textarea, .stNumberInput input, .stTextInput input {
    background: rgba(255,255,255,0.08) !important;
    color: #EAF1F8 !important;
    border-radius: 10px !important;
    border: 1px solid rgba(255,255,255,0.18) !important;
}
</style>
""", unsafe_allow_html=True)

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
            st.warning(
                f"Couldn't find price/quote details in '{f.name}'. "
                "Skipping this file -- please check it's a vendor quote."
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
        st.info(recommendation)

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
        st.warning("Upload at least 2 valid vendor quotes to compare and score them.")

else:
    st.write("Waiting for quotes to be uploaded.")