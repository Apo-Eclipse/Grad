from agents import Orchestrator, Visualizer, Writer
from langgraph.graph import StateGraph, END, START
from typing import Literal,TypedDict, Annotated
from langgraph.types import Command
from operator import add


class PresentationState(TypedDict):
    insights: str
    visualization: str
    report: str
    next_step: Annotated[list[str], add]
    final_output: str
    

def orchestrator(state: PresentationState) -> Literal['Visualizer', 'Writer', 'end']:
    report = state.get("report", "empty")
    visualization = state.get("visualization", "empty")
    
    Output = Orchestrator.invoke({'report': report, 'visualization': visualization})
    next_step = Output.next_step
    print(f"Orchestrator decided next step: {next_step}")
    
    if next_step != "end":
        return Command(
            update={"next_step": [next_step]},
            goto=next_step
        )
    else:
        
        return Command(
            update={"next_step": [next_step], "final_output": f"Report:\n{report}\nVisualizations :\n{visualization}"},
            goto=END
        )

def visualizer(state: PresentationState) -> str:
    insights = state['insights']
    output = Visualizer.invoke({'insights': insights})
    
    return {"visualization": output.visualization}


def writer(state: PresentationState) -> str:
    insights = state['insights']
    output = Writer.invoke({'insights': insights})
    
    return {"report": output.report}


builder = StateGraph(PresentationState)
builder.add_node("Orchestrator", orchestrator)
builder.add_node("Visualizer", visualizer)
builder.add_node("Writer", writer)


builder.add_edge(START, "Orchestrator")
builder.add_edge("Visualizer", "Orchestrator")
builder.add_edge("Writer", "Orchestrator")
presentation_super_agent = builder.compile()