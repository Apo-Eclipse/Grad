import streamlit as st
import os
import re
import glob
import datetime
import pandas as pd
from typing import List, Optional

# PDF and OCR Processing
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io
import cv2
import numpy as np

# LangChain, Torch, and Embeddings
import torch
from sentence_transformers import SentenceTransformer
from langchain.vectorstores import FAISS
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.docstore.document import Document
from langchain_experimental.text_splitter import SemanticChunker

# OpenAI
from openai import OpenAI

# =============================
# INITIAL SETUP
# =============================
# --- Tesseract Path Configuration ---
try:
    pytesseract.pytesseract.tesseract_cmd = r'C:\Users\zonam\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'
except Exception:
    st.warning("Tesseract executable not found at the specified path. OCR functionality will be disabled.")

# --- OpenAI API Key Configuration ---
# Hardcoding the API key as requested.
client = OpenAI(api_key="your_api_key_here")

# =============================
# HELPER FUNCTIONS
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

def preprocess_text(text: str) -> str:
    """Cleans and normalizes Arabic text with safer methods for OCR output."""
    processed_text = re.sub(r'\s+', ' ', text)
    processed_text = processed_text.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    processed_text = processed_text.replace("ة", "ه")
    processed_text = processed_text.replace("ى", "ي")
    return processed_text.strip()

# =============================
# CORE CLASSES
# =============================
class KnowledgeBase:
    """Manages loading, chunking, embedding, and storing document knowledge."""
    def __init__(self, cache_path="pdf_knowledge_base.faiss"):
        self.embeddings = HuggingFaceEmbeddings(model_name="intfloat/multilingual-e5-base")
        self.vectorstore = None
        self.cache_path = cache_path

    def load(self, pdf_paths: Optional[List[str]] = None, pdf_folder: Optional[str] = None, force_rebuild: bool = False):
        if not force_rebuild and os.path.exists(self.cache_path):
            self.vectorstore = FAISS.load_local(self.cache_path, self.embeddings, allow_dangerous_deserialization=True)
            st.sidebar.info("Loaded knowledge base from cache.")
            return

        content_to_process = []
        if pdf_paths:
            for path in pdf_paths:
                text = extract_text_with_enhanced_tesseract(path) # Using the proven OCR method
                if text:
                    metadata = {"source": path, "title": os.path.basename(path), "type": "local"}
                    content_to_process.append((text, metadata))

        if pdf_folder and os.path.exists(pdf_folder):
            for path in glob.glob(os.path.join(pdf_folder, "*.pdf")):
                text = extract_text_with_enhanced_tesseract(path) # Using the proven OCR method
                if text:
                    metadata = {"source": path, "title": os.path.basename(path), "type": "local-folder"}
                    content_to_process.append((text, metadata))
        
        if not content_to_process:
            st.warning("No PDF documents found or processed. Knowledge base is empty.")
            return

        text_splitter = SemanticChunker(self.embeddings)
        all_docs = []
        for text, metadata in content_to_process:
            cleaned_text = preprocess_text(text)
            chunks = text_splitter.split_text(cleaned_text)
            for chunk in chunks:
                all_docs.append(Document(page_content=chunk, metadata=metadata))

        if all_docs:
            self.vectorstore = FAISS.from_documents(all_docs, self.embeddings)
            self.vectorstore.save_local(self.cache_path)

    def retrieve(self, query: str, k: int = 3) -> List[Document]:
        if self.vectorstore:
            return self.vectorstore.as_retriever(search_kwargs={"k": k}).get_relevant_documents(query)
        return []

class LegalAgent:
    """The agent that uses the KnowledgeBase to answer questions."""
    def __init__(self, knowledge_base: KnowledgeBase):
        self.knowledge_base = knowledge_base

    def respond(self, query: str, k: int = 2) -> str:
        retrieved = self.knowledge_base.retrieve(query, k=k)
        context = "\n\n".join([doc.page_content for doc in retrieved[:k]]) if retrieved else ""
        sources = list(set(doc.metadata.get("title") or doc.metadata.get("source") for doc in retrieved))

        if not context.strip():
            return "I'm sorry, but the provided documents do not contain enough information to answer this question.\n\n**Sources:** None"

        draft_prompt = f"""You are a specialized legal assistant for Egyptian law. Your task is to answer the user's query **exclusively** based on the provided context below. **Do not use any external knowledge.** If the context does not contain enough information, you must state that you cannot answer.\n\nQuery: {query}\n\nContext:\n---\n{context}\n---\n\nBased **only** on the context above, draft an answer."""
        draft_response = client.chat.completions.create(
            model="gpt-4o-mini", messages=[{"role": "user", "content": draft_prompt}]
        ).choices[0].message.content

        correction_prompt = f"""You are a strict corrective reviewer. Your only task is to review the draft answer and ensure it adheres to one single rule: **the answer must be 100% based on the provided "Context".**\n\n1. **Verify every statement** in the draft against the "Context".\n2. **Remove any information or detail** that is not explicitly supported by the "Context".\n3. **Do not add new information**.\n4. If the context is insufficient, your final response **must be**: "I'm sorry, but the provided documents do not contain enough information to answer this question."\n\nContext:\n---\n{context}\n---\n\nDraft Answer to Review:\n---\n{draft_response}\n---\n\nFinal, strictly corrected answer based **only** on the "Context" provided:"""
        corrected_response = client.chat.completions.create(
            model="gpt-4o-mini", messages=[{"role": "user", "content": correction_prompt}]
        ).choices[0].message.content

        if "sorry" in corrected_response.lower() and "not contain enough information" in corrected_response.lower():
            return corrected_response + "\n\n**Sources:** None"
        else:
            return corrected_response + f"\n\n**Sources:** {', '.join(sources) if sources else 'None'}"

# =============================
# LOGGING
# =============================
LOG_FILE = "legal_advisor_logs.csv"
def save_log(query, response):
    log_entry = {"timestamp": datetime.datetime.now().isoformat(), "query": query, "response": response}
    df = pd.DataFrame([log_entry])
    header = not os.path.exists(LOG_FILE)
    df.to_csv(LOG_FILE, mode="a", header=header, index=False, encoding="utf-8")

def load_logs():
    return pd.read_csv(LOG_FILE) if os.path.exists(LOG_FILE) else pd.DataFrame(columns=["timestamp", "query", "response"])

# =============================
# STREAMLIT APP INTERFACE
# =============================
st.title("⚖️ Egyptian Financial Legal Advisor")

st.sidebar.title("Data Sources")
uploaded_pdfs = st.sidebar.file_uploader("Upload Local PDFs", type=["pdf"], accept_multiple_files=True)
pdf_folder = st.sidebar.text_input("Or, use PDF Folder Path", value="")
force_rebuild = st.sidebar.checkbox("Force Re-build Knowledge Base", value=False)

if st.sidebar.button("Load Knowledge Base"):
    with st.spinner("Processing documents... This may take a while with OCR and semantic chunking."):
        pdf_paths = []
        if uploaded_pdfs:
            os.makedirs("uploads", exist_ok=True)
            for uploaded in uploaded_pdfs:
                file_path = os.path.join("uploads", uploaded.name)
                with open(file_path, "wb") as f: f.write(uploaded.getbuffer())
                pdf_paths.append(file_path)

        knowledge_base = KnowledgeBase()
        knowledge_base.load(pdf_paths=pdf_paths, pdf_folder=pdf_folder, force_rebuild=force_rebuild)
        st.session_state['legal_agent'] = LegalAgent(knowledge_base=knowledge_base)
        st.sidebar.success("Knowledge base is ready!")

# Main chat interface
if 'legal_agent' in st.session_state:
    st.session_state.messages = st.session_state.get("messages", [])
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])

    if prompt := st.chat_input("Ask a legal question based on the provided PDFs..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Analyzing..."):
                response = st.session_state['legal_agent'].respond(prompt)
                st.markdown(response)
                save_log(prompt, response)
        st.session_state.messages.append({"role": "assistant", "content": response})
else:
    st.info("Please provide PDFs and click 'Load Knowledge Base' in the sidebar to begin.")

# Log viewer in the sidebar
if st.sidebar.button("Show Interaction Logs"):
    st.sidebar.subheader("Logs")
    st.sidebar.dataframe(load_logs())