from agents import Behaviour_Analyst
from langgraph.graph import StateGraph, END, START
from typing import Literal,TypedDict, Annotated
from langgraph.types import Command
import pandas as pd
from operator import add
import json
import sqlite3

class BehaviourAnalystState(TypedDict):
    final_output: str
    result: str

def behaviour_analyst(state: BehaviourAnalystState) -> Literal['end']:
    Output = Behaviour_Analyst.invoke({"final_output": state["final_output"], "result": state["result"]})
    jarray = json.loads(Output.final_output)
    conn = sqlite3.connect("D:/projects/Multi-Agent System/data/database.db")
    # create json to store the results
    results = []
    for item in jarray:
        step = item["step"]
        query = item["query"]
        description = item["description"]
        table = pd.read_sql(query, conn)
        results.append({"step": step, "description": description,"query": query, "result": table})
    return {"final_output": Output.final_output, "result": results}

builder = StateGraph(BehaviourAnalystState)
builder.add_node("behaviour_analyst", behaviour_analyst)
builder.add_edge(START, "behaviour_analyst")
behaviour_analyst_super_agent = builder.compile()