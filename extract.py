import streamlit as st
import os
import re
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io
import cv2
import numpy as np
import easyocr

# =============================
# INITIAL SETUP
# =============================
# --- Tesseract Path Configuration ---
# This line tells the script where to find the Tesseract program.
try:
    pytesseract.pytesseract.tesseract_cmd = r'C:\Users\zonam\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'
except Exception:
    st.warning("Tesseract executable not found at the specified path. OCR functionality will be disabled.")

# =============================
# EXTRACTION & PREPROCESSING FUNCTIONS
# =============================
def extract_text_with_enhanced_tesseract(pdf_path: str) -> str:
    """Extracts text using Tesseract after applying OpenCV pre-processing to each page."""
    st.info(f"Processing {os.path.basename(pdf_path)} with Enhanced Tesseract OCR...")
    full_text = ""
    try:
        with fitz.open(pdf_path) as doc:
            for page_num, page in enumerate(doc):
                with st.spinner(f"Analyzing page {page_num + 1}/{len(doc)}..."):
                    pix = page.get_pixmap(dpi=300)
                    img_data = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
                    
                    gray_image = cv2.cvtColor(img_data, cv2.COLOR_RGB2GRAY)
                    _, threshold_image = cv2.threshold(gray_image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

                    full_text += pytesseract.image_to_string(threshold_image, lang='ara') + "\n"
        return full_text
    except Exception as e:
        st.error(f"An error occurred during enhanced Tesseract processing: {e}")
        return ""

# Use caching to load the EasyOCR model only once
@st.cache_resource
def get_ocr_reader():
    """Initializes the EasyOCR reader."""
    return easyocr.Reader(['ar'])

def extract_text_with_easyocr(pdf_path: str) -> str:
    """Extracts text from a PDF using the EasyOCR library."""
    st.info(f"Processing {os.path.basename(pdf_path)} with EasyOCR...")
    reader = get_ocr_reader()
    full_text = ""
    try:
        with fitz.open(pdf_path) as doc:
            for page_num, page in enumerate(doc):
                with st.spinner(f"Analyzing page {page_num + 1}/{len(doc)}..."):
                    pix = page.get_pixmap(dpi=300)
                    img_bytes = pix.tobytes("png")
                    
                    result = reader.readtext(img_bytes, paragraph=True)
                    page_text = "\n".join([paragraph[1] for paragraph in result])
                    full_text += page_text + "\n"
        return full_text
    except Exception as e:
        st.error(f"An error occurred during EasyOCR processing: {e}")
        return ""

# --- FIXED PREPROCESSING FUNCTION ---
def preprocess_text(text: str) -> str:
    """Cleans and normalizes Arabic text with safer methods for OCR output."""
    # 1. Normalize all whitespace (spaces, newlines, tabs) to a single space.
    processed_text = re.sub(r'\s+', ' ', text)
    
    # 2. Perform the standard character normalizations, which are generally safe.
    processed_text = processed_text.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    processed_text = processed_text.replace("ة", "ه")
    processed_text = processed_text.replace("ى", "ي")

    return processed_text.strip()

# =============================
# STREAMLIT APP INTERFACE
# =============================
st.title("🔬 PDF Text Extraction Tester")
st.markdown("Upload a single PDF to test and compare different OCR methods. The goal is to see clean, readable Arabic text in the output boxes below.")

# --- Sidebar for controls ---
with st.sidebar:
    st.header("Controls")
    uploaded_file = st.file_uploader("Choose a PDF file to test", type="pdf")
    
    extraction_method = st.radio(
        "Choose OCR Method:",
        ("Enhanced Tesseract", "EasyOCR"),
        help="Select which OCR engine to use for the extraction."
    )

    if st.button("Extract Text from PDF"):
        if uploaded_file is not None:
            # Save the file temporarily to a dedicated folder
            temp_dir = "extraction_test_uploads"
            os.makedirs(temp_dir, exist_ok=True)
            file_path = os.path.join(temp_dir, uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            st.session_state['processing_done'] = False
            with st.spinner(f"Running {extraction_method}... This can take several minutes."):
                raw_text = ""
                if extraction_method == "Enhanced Tesseract":
                    raw_text = extract_text_with_enhanced_tesseract(file_path)
                elif extraction_method == "EasyOCR":
                    raw_text = extract_text_with_easyocr(file_path)
                
                st.session_state['extracted_text'] = raw_text
                st.session_state['method_used'] = extraction_method
                st.session_state['file_name'] = uploaded_file.name
                st.session_state['processing_done'] = True
                
        else:
            st.error("Please upload a PDF file first.")

# --- Main area for displaying results ---
if st.session_state.get('processing_done', False):
    st.header(f"Results from: `{st.session_state['method_used']}`")
    st.subheader(f"File: `{st.session_state['file_name']}`")

    raw_text = st.session_state['extracted_text']
    
    if raw_text:
        st.markdown("### Raw Extracted Text")
        st.text_area("Full text extracted from the PDF:", raw_text, height=300)

        st.markdown("---")
        st.markdown("### Pre-processed (Cleaned) Text")
        processed_text = preprocess_text(raw_text)
        st.text_area("Text after cleaning and normalization:", processed_text, height=150)
    else:
        st.error("No text could be extracted from the document using this method. This indicates a severe issue with the PDF's format or scan quality.") 