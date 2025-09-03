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
    final_work: str
    send_by: str
    

def orchestrator(state: PresentationState) -> Literal['Visualizer', 'Writer', 'end']:
    report = state.get("report", "empty")
    visualization = state.get("visualization", "empty")
    final_work = state.get("final_work", "empty")
    insights = state.get("insights", "empty")
    send_by = state.get("send_by", "empty")
    message = state.get("message", "empty")
    Output = Orchestrator.invoke({'report': report, 'visualization': visualization, 'final_work': final_work, 'insights': insights, 'send_by': send_by, 'message': message})
    next_step = Output.next_step
    final_work = Output.final_work
    
    print("Output :",end="")
    print(Output)
    
    print(f"Orchestrator decided next step: {next_step}")
    
    print("PresentationState :",end="")
    print(PresentationState)

    if next_step != "end":
        return Command(
            update={"next_step": [next_step], "final_work": final_work},
            goto=next_step
        )
    else:
        return Command(
            update={"next_step": [next_step], "final_work": final_work},
            goto=END
        )

def visualizer(state: PresentationState) -> str:
    insights = state['insights']
    output = Visualizer.invoke({'insights': insights, 'message': state.get("message", "empty")})
    return {"visualization": output.visualization, "send_by": "Visualizer"}


def writer(state: PresentationState) -> str:
    insights = state['insights']
    output = Writer.invoke({'insights': insights, 'message': state.get("message", "empty")})
    return {"report": output.report, "send_by": "Writer"}


builder = StateGraph(PresentationState)
builder.add_node("Orchestrator", orchestrator)
builder.add_node("Visualizer", visualizer)
builder.add_node("Writer", writer)


builder.add_edge(START, "Orchestrator")
builder.add_edge("Visualizer", "Orchestrator")
builder.add_edge("Writer", "Orchestrator")
presentation_super_agent = builder.compile()