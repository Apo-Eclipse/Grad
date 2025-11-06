from langchain_cerebras import ChatCerebrasAI
import os

gpt_oss_cerebras_llm = ChatCerebrasAI(
    model_name="gpt-oss-120b",
    api_key=os.getenv("CEREBRAS_API_KEY"),
    temperature=0.7,
    timeout=300,
    max_retries=3
)