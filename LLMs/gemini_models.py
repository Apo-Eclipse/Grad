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

# Lazy-load gemini_embedding to avoid async event loop issues in Waitress
# The GoogleGenerativeAIEmbeddings tries to create async clients at init time
# which fails in synchronous contexts like Waitress threads
_gemini_embedding_cache = None

def get_gemini_embedding():
    """
    Lazy-load Gemini embeddings to avoid event loop issues in production servers.
    
    GoogleGenerativeAIEmbeddings creates async gRPC clients at initialization,
    which requires an active event loop. By deferring this to first use,
    we avoid initialization errors in Waitress (synchronous WSGI server).
    """
    global _gemini_embedding_cache
    try:
        if _gemini_embedding_cache is None:
            _gemini_embedding_cache = GoogleGenerativeAIEmbeddings(
                model="models/gemini-embedding-001", 
                google_api_key=os.getenv("GEMINI_API_KEY")
            )
        return _gemini_embedding_cache
    except Exception as e:
        # If embedding initialization fails, return None
        # Fallback logic should be implemented in calling code
        print(f"Warning: Failed to initialize Gemini embeddings: {e}")
        return None

# Backwards compatibility - can be called as function
gemini_embedding = get_gemini_embedding
