from typing import Literal,TypedDict
from LLMs.gemini_models import gemini_llm
from langgraph.graph import END
from langchain_core.prompts import ChatPromptTemplate
from pydantic import Field, BaseModel

class OrchestratorOutput(BaseModel):
    next_step: Literal['Visualizer', 'Writer', "end"] = Field(..., description="The next agent to handle the task: visualizer, writer, or end if the task is complete.")
    report: str = Field(..., description="what is written by the writer agent")
    visualization: str = Field(..., description="what is visualized by the visualizer agent")
    final_work: str = Field(..., description="Combined version of (html,css,js) integrate the writings and the visualization")
    message: str = Field(..., description="Any additional messages or instructions")
    
system_prompt = """
    You are the Orchestrator Agent.
    Based on the report provided, decide which agent should handle the next step.
    Decide where to route this:
    - If this visualization is empty or wants any more or better graphs or visual insights -> return visualizer
    - If report is empty or want to be written in a presentable way -> return Writer
    - If the task is complete and both report and visualizations are good enough and final_work is done -> return end
    - If the user wants to add more insights or details -> return Writer
    - After all work done is integrated into the final output and add the writings with the visualizations in a presentable way with (html,css,js)
    - You have to respond with what was written and the visualization and the integrated work together in (html,css,js)
    - You have to give message to the next agent
    Formate:
    {{
        "report": "{report}",
        "visualization": "{visualization}",
        "final_work": "(html,css,js) page contain combinations of what was done by the 2 agents from visualizations and what was written",
        "next_step": "the agent that should handle the next step",
        "message": "Any additional messages or instructions to the next agent"
    }}
"""

user_prompt = """
    Report: {report}
    visualization: {visualization}
    message send by {send_by} : {message}
    Decide the next step based on the above information.
    Final Work done till now: {final_work}
"""

prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt), 
    ("human", user_prompt)
])


Orchestrator = prompt | gemini_llm.with_structured_output(OrchestratorOutput)
