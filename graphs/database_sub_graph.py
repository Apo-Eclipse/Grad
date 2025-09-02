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
    
def database_agent(state: DatabaseAgentState) -> Literal['end']:
    request = state.get("request", "")
    Output = DatabaseAgent.invoke({"request": request})
    conn = sqlite3.connect("D:/projects/HR_Chatbot/Data/database.db")
    sql = Output.query  
    table = pd.read_sql(sql, conn)
    conn.close()
    return {"request": sql, "output": table}

builder = StateGraph(DatabaseAgentState)
builder.add_node("database_agent", database_agent)
builder.add_edge(START, "database_agent")
builder.add_edge("database_agent", END)
database_agent_super_agent = builder.compile()