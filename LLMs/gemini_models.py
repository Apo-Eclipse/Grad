import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from helpers import settings, get_setting

gemini_llm = ChatGoogleGenerativeAI(
    api_key=os.getenv("GEMINI_API_KEY"),
    model="gemini-2.5-flash-lite",
    temperature=0.6,
    timeout=None,
    max_retries=2,
)

gemini_embedding = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-001", 
    google_api_key=os.getenv("GEMINI_API_KEY") 
)
