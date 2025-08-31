from typing import Literal,TypedDict
from LLMs.gemini_models import gemini_llm
from langgraph.graph import END
from langchain_core.prompts import ChatPromptTemplate
from pydantic import Field, BaseModel

class OrchestratorOutput(BaseModel):
    next_step: Literal['Visualizer', 'Writer', "end"] = Field(..., description="The next agent to handle the task: visualizer, writer, or end if the task is complete.")

system_prompt = """
    You are the Orchestrator Agent.
    Based on the report provided, decide which agent should handle the next step.
    Decide where to route this:
    - If this visualization is empty or wants any more or better graphs or visual insights -> return visualizer
    - If report is empty or want to be written in a presentable way -> return Writer
    - If the task is complete and both report and visualizations are good enough -> return end
"""

user_prompt = """
    Report: {report}
    visualization: {visualization}
    Decide the next step based on the above information.
"""

prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt), 
    ("human", user_prompt)
])


Orchestrator = prompt | gemini_llm.with_structured_output(OrchestratorOutput)
