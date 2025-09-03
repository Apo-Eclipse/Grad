from agents import DatabaseAgent
from langgraph.graph import StateGraph, END, START
from typing import Literal,TypedDict, Annotated
from langgraph.types import Command
import pandas as pd
from operator import add
import json
import sqlite3

class DatabaseAgentState(TypedDict):
    request: str
    output: str
    
def database_agent(state: DatabaseAgentState):
    request = state.get("request", "")
    out = DatabaseAgent.invoke({"request": request})
    # conn = sqlite3.connect("D:/projects/HR_Chatbot/Data/database.db")
    # sql = state.get("request", "")
    # table = pd.read_sql(sql, conn)
    # conn.close()
    j = json.loads(out.final_output)
    for step in j:
        print("-"*30)
        print("Step:", step['step'])
        print("Query:", step['query'])
        conn = sqlite3.connect("D:/projects/Multi-Agent System/data/database.db")
        table = pd.read_sql(step['query'], conn)
        print("Results:", table)
        conn.close()
    print("-"*30)
    return {"output": out.final_output}

builder = StateGraph(DatabaseAgentState)
builder.add_node("database_agent", database_agent)
builder.add_edge(START, "database_agent")
builder.add_edge("database_agent", END)
database_agent_super_agent = builder.compile()