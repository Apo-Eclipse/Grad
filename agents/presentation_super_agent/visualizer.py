from typing import Literal,TypedDict
from LLMs.gemini_models import gemini_llm
from langgraph.graph import StateGraph, END
from typing import Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from pydantic import Field, BaseModel



class VisualizerOutput(BaseModel):
    visualization: str = Field(..., description="The visualization code in HTML/CSS format.")
    
system_prompt = """
    You are the Graph Maker Agent.
    Convert this insights into visualization code (HTML, CSS, JavaScript):
    Try to include interactive elements where appropriate.
    Leave space for dynamic data loading and user interactions.
"""
user_prompt = """
    insights: {insights}
    message from the orchestrator: {message}
"""

prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("human", user_prompt)
])

Visualizer = prompt | gemini_llm.with_structured_output(VisualizerOutput)
