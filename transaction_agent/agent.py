# agent.py
import os
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from pydantic import BaseModel, Field
from langchain_openai import AzureChatOpenAI
from langchain.agents import AgentExecutor, create_react_agent
from tools import process_audio_transaction
from typing import List


class LineItem(BaseModel):
    """Represents a single item and its price on a receipt."""
    name: str = Field(description="The name of the purchased item.")
    price: float = Field(description="The price of the individual item.")

class Transaction(BaseModel):
    """Represents a single financial transaction."""
    vendor: str = Field(description="The name of the vendor or store.")
    amount: float = Field(description="The total amount of the transaction.")
    date: str = Field(description="The date of the transaction in YYYY-MM-DD format.")
    time: str = Field(description="The time of the transaction in HH:MM format.")
    items: List[LineItem] = Field(description="A list of all line items, each with a name and a price.")

class FinancialAgent:
    """A unified agent to handle text, image, and audio transactions."""
    
    def __init__(self):
        # 1. Agent for Text
        # Support both short and LARGE_ prefixed env var names (some deployments use LARGE_... keys)
        text_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME") or os.getenv("LARGE_AZURE_OPENAI_DEPLOYMENT_NAME")
        api_version = os.getenv("AZURE_OPENAI_API_VERSION") or os.getenv("LARGE_AZURE_OPENAI_API_VERSION")
        text_llm = AzureChatOpenAI(
            deployment_name=text_deployment,
            api_version=api_version,
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        # Use function_calling method for models that do not support json_schema structured output
        structured_text_llm = text_llm.with_structured_output(Transaction, method="function_calling")
        # agent.py - NEW TEXT PROMPT
        text_system_message = "You are an expert at extracting transaction details from text. Given a user's input, identify the vendor, the total amount, date, and all items purchased along with their individual prices."
        text_prompt = ChatPromptTemplate.from_messages([
            ("system", text_system_message),
            ("user", "{input}"),
        ])
        self.text_agent = text_prompt | structured_text_llm

        # 2. Agent for Vision
        vision_deployment = os.getenv("AZURE_OPENAI_VISION_DEPLOYMENT_NAME") or os.getenv("LARGE_AZURE_OPENAI_DEPLOYMENT_NAME") or os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME") or os.getenv("LARGE_AZURE_OPENAI_DEPLOYMENT_NAME")
        vision_llm = AzureChatOpenAI(
            deployment_name=vision_deployment,
            api_version=api_version,
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        structured_vision_llm = vision_llm.with_structured_output(Transaction, method="function_calling")
        vision_prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert at extracting transaction details from receipt images. Extract the vendor, total amount, date and time of purchase, and a list of all line items with their individual prices from this receipt."""),
        ("user", [
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,{image_data}"}}
    ])
])

        self.vision_agent = vision_prompt | structured_vision_llm

        # 3. Agent for Audio
        audio_tools = [process_audio_transaction]
        audio_llm = AzureChatOpenAI(
            deployment_name=text_deployment,
            api_version=api_version,
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        audio_prompt_template = """
        Answer the following questions as best you can. You have access to the following tools:
        {tools}
        Use the following format:
        Question: the input question you must answer
        Thought: you should always think about what to do
        Action: the action to take, should be one of [{tool_names}]
        Action Input: the input to the action
        Observation: the result of the action
        ... (this Thought/Action/Action Input/Observation can repeat N times)
        Thought: I now know the final answer
        Final Answer: the final answer to the original input question
        Begin!
        Question: {input}
        Thought:{agent_scratchpad}
        """
        audio_prompt = PromptTemplate.from_template(audio_prompt_template)
        react_agent = create_react_agent(audio_llm, audio_tools, audio_prompt)
        self.audio_agent = AgentExecutor(agent=react_agent, tools=audio_tools, verbose=True)

    def invoke(self, input_data):
        """
        Dynamically invokes the correct agent based on the input.
        """
        if "image_data" in input_data:
            # It's an image transaction
            return self.vision_agent.invoke({"image_data": input_data["image_data"]})
        elif "audio_path" in input_data:
            # It's an audio transaction
            return self.audio_agent.invoke({"input": input_data["audio_path"]})
        elif "text" in input_data:
            # It's a text transaction
            return self.text_agent.invoke({"input": input_data["text"]})
        else:
            raise ValueError("Invalid input: No 'text', 'image_data', or 'audio_path' key found.")
