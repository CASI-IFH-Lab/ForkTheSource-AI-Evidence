"""ForkTheSource - the web app.

Start it with:

    streamlit run app.py

B0 does one thing: you drop a PDF in and it shows you the raw text it pulled out.
This is the skeleton shell. The real UI is dashboard/app.py (A2, Arsha's).
"""

from __future__ import annotations

import streamlit as st

from src.ingest import pdf_parser

st.set_page_config(page_title="ForkTheSource", page_icon="🍴", layout="wide")


# Streamlit re-runs this whole file on every click, so anything slow gets cached.
# The cache key is the file's bytes: same PDF, no second read.
@st.cache_data(show_spinner="Reading the PDF...")
def read_pdf(pdf_bytes: bytes) -> dict:
    # config is required positional on every stage entry point so P6 can call them
    # all the same way. P1 reads nothing from it, and None says so explicitly.
    return pdf_parser.run(pdf_bytes, None)


st.title("ForkTheSource")
st.caption("Provenance and reproducibility evidence for academic papers. CASI team, ASU AIR.")

uploaded = st.file_uploader(
    "Drop a PDF here",
    type="pdf",
    help="The paper you want checked. Nothing leaves your machine in M0.",
)

if uploaded is None:
    st.info("Drop a PDF above to see the text this app can read out of it.")
    st.stop()

# Later milestones will keep their results in st.session_state, keyed by this name,
# so that clicking around the page does not re-run the whole pipeline.
st.session_state["source_name"] = uploaded.name

result = read_pdf(uploaded.getvalue())
pages = result["pages"]
text = result["text"]

left, middle, right = st.columns(3)
left.metric("Pages", result["page_count"])
middle.metric("Characters", f"{len(text):,}")
right.metric("Pages with no text", sum(1 for page in pages if not page.strip()))

if not text.strip():
    st.error(
        "No text came out of this PDF. It is most likely a scan of a printed page, "
        "which needs OCR - that is out of scope for now."
    )
    st.stop()

st.subheader("Raw extracted text")
st.text_area("Whole document", value=text, height=420, label_visibility="collapsed")

with st.expander("Page by page"):
    for number, page in enumerate(pages, start=1):
        st.markdown(f"**Page {number}**")
        st.text(page if page.strip() else "(no text on this page)")

st.divider()
st.caption(
    "This shell shows raw text only. P1 also returns the body/references split - "
    "`pdf_parser.parse_pdf()` - which P2 turns into contract Reference objects. "
    "See docs/architecture_map.md."
)
