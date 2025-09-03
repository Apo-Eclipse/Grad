from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from helpers import settings, get_setting

app_settings = get_setting()

# embeddings = AzureOpenAIEmbeddings(
#     azure_deployment=app_settings.AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT_NAME,
#     openai_api_version=app_settings.AZURE_OPENAI_EMBEDDING_VERSION,
#     azure_endpoint=app_settings.AZURE_OPENAI_ENDPOINT,
#     api_key=app_settings.AZURE_OPENAI_API_KEY,
# )


# 2. Initialize Azure OpenAI Chat Model (GPT)
# This points to your chat model deployment on Azure.
azure_llm = AzureChatOpenAI(
    azure_deployment=app_settings.AZURE_OPENAI_DEPLOYMENT_NAME,
    openai_api_version=app_settings.AZURE_OPENAI_API_VERSION,
    azure_endpoint=app_settings.AZURE_OPENAI_ENDPOINT,
    api_key=app_settings.AZURE_OPENAI_API_KEY,
    temperature=1,
    max_retries=2,
)