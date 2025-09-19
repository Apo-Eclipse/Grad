from typing import Literal,TypedDict
from LLMs.gemini_models import gemini_llm
from LLMs.azure_models import azure_llm
from langgraph.graph import StateGraph, END
from typing import Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from pydantic import Field, BaseModel
from LLMs.ollama_llm import ollama_llm

class orchestratorOutput(BaseModel):
    message: str = Field(..., description="The message from the agent. (ok if there is no problem and error if there is)")
    next_step: Literal['query_planner', 'analyser', "end"] = Field(..., description="The next agent to handle the task: Query Planner, Behavior Analyst, or end if the task is complete.")
    
system_prompt = """
    You are the Orchestrator Agent.  
    Your task is to coordinate between the Query Planner, analyser, and the end of the process.
    The query planner agent outlines clear and simple steps for another database agent to create SQL-style queries that retrieve insights about a **single user's** behavior and spending patterns.
    The analyser agent analyzes the data retrieved by the database agent and provides insights based on the queries outlined by the query planner.
    Decide where to route this:
    - If the analyser agent ask or recommends for additional data -> return query_planner
    - If the analysis agent not been called-> return analyser
    - If the task is complete and all data gathered -> return end
    Formate:
    {{
        "next_step": "the agent that should handle the next step",
        "message": "Any additional messages or instructions to the next agent"
    }}
    """

user_prompt = """
    Data acquired: {data_acquired}
    analysis done: {analysis} 
    first request: {request}
    message sended from {sender}: {message}
    Based on the above information, decide the next step for the task.
"""

prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("user", user_prompt)
])

Behaviour_analyser_orchestrator = prompt | gemini_llm.with_structured_output(orchestratorOutput)