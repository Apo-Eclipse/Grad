from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from helpers import settings, get_setting
import os

azure_llm = AzureChatOpenAI(
    azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
    openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    max_retries=4,
)

large_azure_llm = AzureChatOpenAI(
    azure_deployment=os.getenv("LARGE_AZURE_OPENAI_DEPLOYMENT_NAME"),
    openai_api_version=os.getenv("LARGE_AZURE_OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    max_retries=4,
)

gpt_oss_llm = AzureChatOpenAI(
    azure_deployment=os.getenv("GPT_OSS_DEPLOYMENT_NAME"),
    openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    timeout=15,
    max_retries=3,
)