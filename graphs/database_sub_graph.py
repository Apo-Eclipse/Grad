from agents import DatabaseAgent
from langgraph.graph import StateGraph, END, START
from typing import TypedDict
import pandas as pd
import sqlite3
import json
import time
class DatabaseAgentState(TypedDict):
    request: str         
    result: dict         

def database_agent(state: DatabaseAgentState):
    step_text = state.get("request", "")
    try:
        out = DatabaseAgent.invoke({"request": step_text, "user": "1"})
        query = out.query
        results = []
        with sqlite3.connect("D:/projects/Multi-Agent System/data/database.db") as conn:
            try:
                df = pd.read_sql(query, conn)
                results = df.to_dict(orient="records")
            except Exception as e:
                results = f"Error Executing Query: {str(e)}"
        return {"result": {"step": step_text, "query": query, "data": results}}
    except Exception as e:
        return {"result": {"step": step_text, "query": None, "data": f"Agent Error: {str(e)}"}}

builder = StateGraph(DatabaseAgentState)
builder.add_node("database_agent", database_agent)
builder.add_edge(START, "database_agent")
builder.add_edge("database_agent", END)
database_agent_super_agent = builder.compile()