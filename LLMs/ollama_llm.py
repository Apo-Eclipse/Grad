from langchain_ollama import ChatOllama

ollama_llm = ChatOllama(
    model="gpt-oss:20b",
    temperature=1,
)