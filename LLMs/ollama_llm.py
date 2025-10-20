from ollama import Client
import os
from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableLambda



client = Client(
    host="https://ollama.com",
    headers={'Authorization': os.getenv("OLLAMA_API_KEY")}
) 

def to_ollama_messages(messages):
    # Handle both ChatPromptTemplate and list of messages
    if hasattr(messages, "format_prompt"):
        prompt_messages = messages.format_prompt().to_messages()
    elif hasattr(messages, "to_messages"):
        prompt_messages = messages.to_messages()
    else:
        prompt_messages = messages

    formatted = []
    for msg in prompt_messages:
        if isinstance(msg, BaseMessage):  # LangChain message object
            role, content = msg.type, msg.content
        else:
            raise TypeError(f"Unsupported message type: {type(msg)}")

        # Map LangChain roles -> Ollama roles
        if role == "human":
            role = "user"
        elif role == "ai":
            role = "assistant"
        elif role == "system":
            role = "system"

        formatted.append({"role": role, "content": content})
    return formatted

def message_formatting(messages):
    ollama_msgs = to_ollama_messages(messages)
    out = client.chat("gpt-oss:120b", messages=ollama_msgs)
    return out["message"]["content"]

gpt_oss = RunnableLambda(message_formatting)