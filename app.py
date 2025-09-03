import streamlit as st
import os
import re
import datetime
import requests
import pandas as pd
import glob
from bs4 import BeautifulSoup
from PyPDF2 import PdfReader
from typing import List, Optional

import torch
from sentence_transformers import SentenceTransformer

# LangChain / FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import FAISS
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.docstore.document import Document

# OpenAI for LLM
from openai import OpenAI
client = OpenAI(api_key="YOUR_OPENAI_API_KEY")

# =============================
# Preprocessing
# =============================
def remove_diacritics(text: str) -> str:
    return re.sub(r'[\u0610-\u065F]', '', text)

def normalize_alef(text: str) -> str:
    return text.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")

def normalize_teh_marbuta(text: str) -> str:
    return text.replace("ة", "ه")

def normalize_alef_maksura(text: str) -> str:
    return text.replace("ى", "ي")

def english_cleanup(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9\s]", "", text).strip()

def general_cleanup(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()

def preprocess_text(text: str, lang: str = "ar") -> str:
    if lang == "ar":
        text = remove_diacritics(text)
        text = normalize_alef(text)
        text = normalize_teh_marbuta(text)
        text = normalize_alef_maksura(text)
    elif lang == "en":
        text = english_cleanup(text)
    return general_cleanup(text)

# =============================
# FRA Scraper
# =============================
def scrape_fra_pdfs(base_url: str, max_pdfs=3):
    response = requests.get(base_url)
    soup = BeautifulSoup(response.text, "html.parser")
    pdf_links = []
    for link in soup.find_all("a", href=True):
        href = link["href"]
        if href.endswith(".pdf"):
            full_url = href if href.startswith("http") else base_url + href
            title = link.get_text(strip=True) or "FRA Document"
            pdf_links.append((full_url, title))
    return pdf_links[:max_pdfs]

def download_and_extract_pdf(url: str) -> str:
    try:
        response = requests.get(url)
        filename = "temp.pdf"
        with open(filename, "wb") as f:
            f.write(response.content)
        reader = PdfReader(filename)
        return "".join([page.extract_text() or "" for page in reader.pages])
    except Exception as e:
        return f"Error reading {url}: {e}"

# =============================
# Knowledge Base
# =============================
class KnowledgeBase:
    def __init__(self, cache_path="fra_index.faiss", max_pdfs=3):
        self.embeddings = HuggingFaceEmbeddings(model_name="intfloat/multilingual-e5-base")
        self.vectorstore = None
        self.cache_path = cache_path
        self.max_pdfs = max_pdfs

    def load(self, pdf_paths: Optional[List[str]] = None, pdf_folder: Optional[str] = None, urls: Optional[List[str]] = None, use_cache=True):
        docs = []

        # Load cached FAISS if available
        if use_cache and os.path.exists(self.cache_path):
            self.vectorstore = FAISS.load_local(self.cache_path, self.embeddings, allow_dangerous_deserialization=True)
            return

        # --- Load PDFs from list ---
        if pdf_paths:
            for path in pdf_paths:
                reader = PdfReader(path)
                raw_text = "".join([page.extract_text() or "" for page in reader.pages])
                cleaned = preprocess_text(raw_text, lang="ar")
                chunks = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50).split_text(cleaned)
                docs.extend([Document(page_content=c, metadata={"source": path}) for c in chunks])

        # --- Load PDFs from folder ---
        if pdf_folder and os.path.exists(pdf_folder):
            all_pdfs = glob.glob(os.path.join(pdf_folder, "*.pdf"))
            for path in all_pdfs:
                reader = PdfReader(path)
                raw_text = "".join([page.extract_text() or "" for page in reader.pages])
                cleaned = preprocess_text(raw_text, lang="ar")
                chunks = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50).split_text(cleaned)
                docs.extend([Document(page_content=c, metadata={"source": path}) for c in chunks])

        # --- Load FRA PDFs ---
        if urls:
            for url in urls:
                fra_pdfs = scrape_fra_pdfs(url, self.max_pdfs)
                for pdf_url, title in fra_pdfs:
                    pdf_text = download_and_extract_pdf(pdf_url)
                    cleaned = preprocess_text(pdf_text, lang="ar")
                    chunks = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50).split_text(cleaned)
                    docs.extend([Document(page_content=c, metadata={"title": title, "source": pdf_url}) for c in chunks])

        # --- Save vectorstore ---
        if docs:
            self.vectorstore = FAISS.from_documents(docs, self.embeddings)
            self.vectorstore.save_local(self.cache_path)

    def retrieve(self, query: str, k: int = 3) -> List[str]:
        if self.vectorstore:
            docs = self.vectorstore.as_retriever(search_kwargs={"k": k}).get_relevant_documents(query)
            return [doc.page_content for doc in docs]
        return []

# =============================
# Agent
# =============================
class Agent:
    def __init__(self, name: str, knowledge_base: KnowledgeBase, search_knowledge=True):
        self.name = name
        self.knowledge_base = knowledge_base
        self.search_knowledge = search_knowledge

    def respond(self, query: str, k: int = 2) -> str:
        context = ""
        if self.search_knowledge:
            retrieved = self.knowledge_base.retrieve(query, k=k)
            if retrieved:
                context = "\n\nRelevant Regulations:\n" + "\n".join(retrieved[:k])

        prompt = f"""
        You are a legal advisor specialized in Egyptian financial law.
        Answer clearly and concisely.
        Query: {query}
        {context}
        """

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content

# =============================
# Logs Manager
# =============================
LOG_FILE = "legal_logs.csv"

def save_log(query, response):
    log_entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "query": query,
        "response": response
    }
    df = pd.DataFrame([log_entry])
    if os.path.exists(LOG_FILE):
        df.to_csv(LOG_FILE, mode="a", header=False, index=False, encoding="utf-8")
    else:
        df.to_csv(LOG_FILE, index=False, encoding="utf-8")

def load_logs():
    if os.path.exists(LOG_FILE):
        return pd.read_csv(LOG_FILE)
    return pd.DataFrame(columns=["timestamp", "query", "response"])

# =============================
# Streamlit App
# =============================
st.title("Legal Advisor")

st.sidebar.title("Configuration")
fra_url = st.sidebar.text_input("FRA URL", value="https://fra.gov.eg/التشريعات-العامة-للهيئة1/")
max_pdfs = st.sidebar.number_input("Max FRA PDFs to load", min_value=1, max_value=10, value=3)

# Upload PDFs
uploaded_pdfs = st.sidebar.file_uploader("Upload PDFs", type=["pdf"], accept_multiple_files=True)

# Folder of PDFs
pdf_folder = st.sidebar.text_input("PDF Folder Path", value="")

if st.sidebar.button("Load Knowledge Base"):
    with st.spinner("Loading knowledge base..."):
        pdf_paths = []
        if uploaded_pdfs:
            os.makedirs("uploads", exist_ok=True)
            for uploaded in uploaded_pdfs:
                file_path = os.path.join("uploads", uploaded.name)
                with open(file_path, "wb") as f:
                    f.write(uploaded.read())
                pdf_paths.append(file_path)

        knowledge_base = KnowledgeBase(max_pdfs=max_pdfs)
        knowledge_base.load(pdf_paths=pdf_paths, pdf_folder=pdf_folder if pdf_folder else None, urls=[fra_url])
        legal_agent = Agent(name="LegalAdvisor", knowledge_base=knowledge_base)
        st.session_state['legal_agent'] = legal_agent
        st.sidebar.success("Knowledge base ready ✅")

# Chat
if 'legal_agent' in st.session_state:
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Ask a legal question..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Analyzing..."):
                response = st.session_state['legal_agent'].respond(prompt)
                st.markdown(response)
                save_log(prompt, response)

        st.session_state.messages.append({"role": "assistant", "content": response})

# Logs
if st.sidebar.button("Show Logs"):
    logs_df = load_logs()
    st.sidebar.dataframe(logs_df)
