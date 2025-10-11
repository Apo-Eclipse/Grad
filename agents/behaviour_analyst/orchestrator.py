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
You are the Orchestrator, the central decision-maker in a data analysis pipeline.
Your mission is to evaluate the task's current state and route it to the next logical step to answer a user's request.

You will receive the following context:
- user_request: The user's original question.
- data_acquired: The data retrieved so far.
- analysis: The insights generated from the data.
- sender: The agent that provided the last message.
- message: The content of the last message.

### Your Decision-Making Logic (Evaluate in this strict order)

1.  **Check for analyser's Explicit Request for Data:**
    - **Condition:** If the `sender` is 'analyser' AND its `message` clearly states that more information or data is required to proceed.
    - **Action:** Immediately route to `query_planner`. Your message to the planner should be based on the analyser's specific request.

2.  **Assess Data Sufficiency:**
    - **Condition:** If the current `data_acquired` is insufficient to fully answer the `user_request`.
    - **Action:** Route to `query_planner`. Your message must specify what information is still missing.

3.  **Assess Analysis Quality:**
    - **Condition:** If the `data_acquired` IS sufficient, but the `analysis` is incomplete, inaccurate, or does not address the `user_request`.
    - **Action:** Route to `analyser`. Your message must provide specific feedback for improvement.

4.  **Determine Task Completion:**
    - **Condition:** If the data is sufficient AND the analysis is high-quality and directly answers the `user_request`.
    - **Action:** Route to `end`. Your message should be a final confirmation.

### Output Format
You MUST respond with a single, valid JSON object:
{{
    "next_step": "query_planner | analyser | end",
    "message": "A clear, concise message or instruction for the next step."
}}
"""

# This user prompt template cleanly presents the state for the agent to evaluate.
user_prompt = """
Current Task State:
- User Request: {request}
- Data Acquired: {data_acquired}
- Analysis Done: {analysis}
- Last Message From: '{sender}'
- Last Message Content: "{message}"

Based on the current state, decide the next step.
"""

prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("user", user_prompt)
])

Behaviour_analyser_orchestrator = prompt | large_azure_llm.with_structured_output(orchestratorOutput, method="function_calling")