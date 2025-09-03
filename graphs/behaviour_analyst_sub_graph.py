from agents import Behaviour_Analyst
from langgraph.graph import StateGraph, END, START
from typing import Literal,TypedDict, Annotated
from langgraph.types import Command
import pandas as pd
from operator import add

class BehaviourAnalystState(TypedDict): 
    returned: str

def behaviour_analyst(state: BehaviourAnalystState):
    Output = Behaviour_Analyst.invoke({})
    if Output.message == "error":
        print(Output.output)
        return
    return {"returned": Output}

builder = StateGraph(BehaviourAnalystState)
builder.add_node("behaviour_analyst", behaviour_analyst)
builder.add_edge(START, "behaviour_analyst")
builder.add_edge("behaviour_analyst", END)
behaviour_analyst_super_agent = builder.compile()