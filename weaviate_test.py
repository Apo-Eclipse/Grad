from dotenv import load_dotenv

# Load environment variables
load_dotenv()
import os
import weaviate
from weaviate.auth import AuthApiKey
from langchain_weaviate.vectorstores import WeaviateVectorStore
from langchain_core.documents import Document
from LLMs.azure_models import embeddings

# Connect using v4 syntax
client = weaviate.connect_to_weaviate_cloud(
    cluster_url=os.getenv("weaviate_cluster_url"),
    auth_credentials=AuthApiKey(os.getenv("weaviate_api_key"))
)

user_id = "user_12345"  # Example user ID for tenant isolation

try:
    # Create vector store with tenant specified
    # vector_store = WeaviateVectorStore.from_documents(
    #     documents=[Document(page_content="This is a sample document.", metadata={"source": "sample.txt"})],
    #     client=client,
    #     index_name="Episodic_memory",
    #     embedding=embeddings,
    #     tenant=f"{user_id}"  # Add tenant parameter
    # )
    vector_store = WeaviateVectorStore(
    client=client,
    index_name="Episodic_memory",
    embedding=embeddings,
    text_key="text",
    )
    
    vector_store_2 = WeaviateVectorStore(
    client=client,
    index_name="Semantic_memory",
    embedding=embeddings,
    text_key="text",
    )
    
    
    print("Vector store created successfully!")
    

    
    query = "sample document"
    results = vector_store.similarity_search(query, tenant=f"{user_id}")
    for doc in results:
        print(doc)

    
finally:
    client.close()