from typing import Literal,TypedDict
from LLMs.azure_models import large_azure_llm 
from langgraph.graph import StateGraph, END
from typing import Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from pydantic import Field, BaseModel
from LLMs.ollama_llm import ollama_llm

class orchestratorOutput(BaseModel):
    message: str = Field(..., description="The message from the agent. (ok if there is no problem and error if there is)")
    next_step: Literal['query_planner', 'analyser', "end"] = Field(..., description="The next agent to handle the task: Query Planner, Behavior Analyst, or end if the task is complete.")
    
system_prompt = """
You are the Orchestrator Agent, a critical decision-maker in a data processing pipeline.
Your primary role is to evaluate the progress of a task and intelligently decide the next step.
You will route the task to the 'query_planner' for more data, the 'analyzer' for better insights, or 'end' the process if the user's request is fully satisfied.

You will be given the following information:
- user_request: The original question the user asked.
- data_acquired: The raw data retrieved to answer the request.
- analysis: The summary and insights generated from the data.

### Your Decision-Making Process
Evaluate the inputs in the following order to determine the next step:

1.  **Assess Data Sufficiency vs. User Request**
    - **Question**: Is the `data_acquired` comprehensive enough to fully and directly answer the `user_request`?
    - If **NO**, the necessary information is missing. The planner needs to formulate new queries.
    - **Action** -> Route to `query_planner`. The message must specify what information is still needed.

2.  **Assess Analysis Quality vs. Acquired Data**
    - **Question**: *If the data is sufficient*, does the `analysis` accurately and completely interpret the `data_acquired` to answer the `user_request`?
    - If **NO**, the analysis is flawed, incomplete, or misses the point of the user's question.
    - **Action** -> Route to `analyzer`. The message must provide specific feedback on how to improve the analysis.

3.  **Determine Task Completion**
    - **Question**: *If the data is sufficient AND the analysis is high-quality* and directly answers the `user_request`?
    - If **YES**, the task is complete.
    - **Action** -> Route to `end`. The message should confirm that the request has been fully addressed.

### Output Format
You MUST respond in a valid JSON format:
{{
    "next_step": "query_planner | analyzer | end",
    "message": "Clear, concise instructions or a final summary for the next step."
}}
"""

user_prompt = """
Data acquired: {data_acquired}
Analysis done: {analysis}
User request: {request}
User: {user}
Message sent from {sender}: {message}

Based on the above information, decide the next step for the task.
"""

prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("user", user_prompt)
])

Behaviour_analyser_orchestrator = prompt | large_azure_llm.with_structured_output(orchestratorOutput, method="function_calling")