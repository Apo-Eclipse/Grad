from langchain_google_genai import ChatGoogleGenerativeAI
from helpers import settings, get_setting

app_settings = get_setting()

gemini_llm = ChatGoogleGenerativeAI(
    api_key=app_settings.GEMINI_API_KEY,
    model="gemini-2.5-flash-lite",
    temperature=0.6,
    timeout=None,
    max_retries=2,
)