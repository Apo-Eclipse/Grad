from typing import Literal,TypedDict
from LLMs.gemini_models import gemini_llm
from langgraph.graph import StateGraph, END
from langchain_core.prompts import ChatPromptTemplate
from pydantic import Field, BaseModel

class WriterOutput(BaseModel):
    report: str = Field(..., description="The final written report.")

system_prompt = """
    You are the Writer Agent.
    Summarize the insights provided into a clean, structured appealling report to read.
    Only respond with the final output of summary of the insights and make it like a conversation not points with subtitles.
    Try to make it in good format to read.
"""

user_prompt = """
    insights: {insights}
"""

prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt), 
    ("human", user_prompt)
])


Writer = prompt | gemini_llm.with_structured_output(WriterOutput)