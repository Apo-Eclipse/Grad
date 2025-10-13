# LegalAdvisorAgent_streamlit.py
# Interactive Legal Advisor Agent with Query-RAG
# Features:
# - Chatbot interface (multi-turn, like ChatGPT)
# - Query rewriting + FAISS retrieval
# - LLM answers in user's language with clarifications if needed
# - Logs every turn automatically into CSV (no manual download)

import os
import json
import time
import streamlit as st
import pandas as pd
from typing import List, Dict, Any, Tuple

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from openai import OpenAI

# --- Config ----------------------------------------------------------------
KB_JSON_PATH = "C:/Users/saifk/OneDrive/Desktop/Legal Adv/egypt_finance_kb.json"
FAISS_INDEX_PATH = "faiss_index.idx"
EMBEDDINGS_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
TOP_K = 6
CSV_LOG_FILE = "agent_logs.csv"

client = OpenAI(api_key="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")
MODEL_NAME = "gpt-4o-mini"

SYSTEM_PROMPT = r"""
You are "Egypt Financial Legal Advisor" — a professional compliance officer and lawyer specializing in Egyptian financial and fintech law.
Behaviors:
- Always respond in the user's language (Arabic if the user's text contains Arabic characters; English otherwise).
- Rely primarily on Retrieved Context (KB); use internal knowledge for missing details.
- If info is insufficient, ask ONE clarifying question before answering.
- Cite laws and regulations (with title, id, and source_url).
- Refuse politely if asked for illegal/unethical advice.
- Keep answers concise and practical.

Output JSON:
{
  "answer_text": "...",
  "language": "ar|en",
  "sources": [{"id":"..","title":"..","confidence":0.0,"source_url":"..."}],
  "confidence": 0.0,
  "action": "answer|clarify|escalate|refuse",
  "clarifying_question": "..."
}
"""

# --- JSON extractor --------------------------------------------------------
def extract_json_object_from_text(text: str) -> dict:
    start = text.find("{")
    if start == -1:
        return {}
    stack, end_idx = [], None
    for i in range(start, len(text)):
        if text[i] == "{":
            stack.append("{")
        elif text[i] == "}":
            stack.pop()
            if not stack:
                end_idx = i
                break
    if end_idx is None:
        return {}
    try:
        return json.loads(text[start:end_idx + 1])
    except Exception:
        return {}

# --- KB + FAISS ------------------------------------------------------------
def load_kb(path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        kb = json.load(f)
        return kb if isinstance(kb, list) else []

def build_index(kb: List[Dict[str, Any]]):
    texts = [entry.get("text", "")[:1000] for entry in kb]
    ids = [entry.get("id", str(i)) for i, entry in enumerate(kb)]
    model = SentenceTransformer(EMBEDDINGS_MODEL_NAME)
    embeddings = model.encode(texts, convert_to_numpy=True)
    faiss.normalize_L2(embeddings)
    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)
    with open(FAISS_INDEX_PATH + ".ids", "w", encoding="utf-8") as f:
        for i in ids: f.write(i + "\n")
    faiss.write_index(index, FAISS_INDEX_PATH)
    return index, ids

def load_index():
    index = faiss.read_index(FAISS_INDEX_PATH)
    ids = [line.strip() for line in open(FAISS_INDEX_PATH + ".ids", "r", encoding="utf-8")]
    return index, ids

def embed_query(q: str):
    model = SentenceTransformer(EMBEDDINGS_MODEL_NAME)
    emb = model.encode([q], convert_to_numpy=True)[0]
    faiss.normalize_L2(emb.reshape(1, -1))
    return emb

def retrieve(query: str, kb, index, ids, k=TOP_K):
    q_emb = embed_query(query).astype("float32")
    D, I = index.search(q_emb.reshape(1, -1), k)
    results = []
    for score, idx in zip(D[0], I[0]):
        if idx >= 0:
            eid = ids[idx]
            entry = next((e for e in kb if e["id"] == eid), None)
            if entry: results.append((entry, float(score)))
    return results

# --- Language detection ----------------------------------------------------
def detect_language(text: str) -> str:
    for ch in text:
        if "\u0600" <= ch <= "\u06FF":
            return "ar"
    return "en"

# --- Query rewriting -------------------------------------------------------
def rewrite_query(query: str, lang: str) -> str:
    messages = [
        {"role": "system", "content": "Rewrite queries into precise Egyptian legal search queries."},
        {"role": "user", "content": f"Rewrite this {lang} query for legal retrieval:\n{query}"}
    ]
    resp = client.chat.completions.create(model=MODEL_NAME, messages=messages, temperature=0, max_tokens=100)
    return resp.choices[0].message.content.strip()

def retrieve_with_rewriting(query, kb, index, ids):
    lang = detect_language(query)
    rewritten = rewrite_query(query, lang)
    results = retrieve(query, kb, index, ids) + retrieve(rewritten, kb, index, ids)
    merged = {}
    for entry, score in results:
        if entry["id"] not in merged or score > merged[entry["id"]][1]:
            merged[entry["id"]] = (entry, score)
    return list(merged.values())

# --- LLM answering ---------------------------------------------------------
def call_llm(query, retrieved, lang, history):
    ctx = "\n\n".join([f"[{r[0]['id']}] {r[0]['title']}: {r[0]['text'][:600]}" for r in retrieved])
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history + [
        {"role": "user", "content": f"User Query: {query}\n\nRetrieved Context:\n{ctx}\n\nLanguage: {lang}"}
    ]
    resp = client.chat.completions.create(model=MODEL_NAME, messages=messages, temperature=0, max_tokens=800)
    return resp.choices[0].message.content

# --- Logging ---------------------------------------------------------------
def save_to_csv(query: str, parsed: dict):
    row = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "query": query,
        "answer_text": parsed.get("answer_text", ""),
        "language": parsed.get("language", ""),
        "confidence": parsed.get("confidence", 0),
        "action": parsed.get("action", ""),
        "clarifying_question": parsed.get("clarifying_question", "")
    }
    for i, src in enumerate(parsed.get("sources", []), start=1):
        row[f"source{i}_title"] = src.get("title", "")
        row[f"source{i}_url"] = src.get("source_url", "")
        row[f"source{i}_confidence"] = src.get("confidence", 0)
    df = pd.DataFrame([row])
    if not os.path.exists(CSV_LOG_FILE):
        df.to_csv(CSV_LOG_FILE, index=False)
    else:
        df.to_csv(CSV_LOG_FILE, mode="a", index=False, header=False)

