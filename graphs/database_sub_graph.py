import pandas as pd
import asyncio
import asyncpg  
import os
from typing import TypedDict
from langgraph.graph import StateGraph, END, START
from agents import DatabaseAgent

class DatabaseAgentState(TypedDict):
    request: str
    result: dict

# --- ASYNC Node Definition ---
async def database_agent(state: DatabaseAgentState) -> dict:
    """
    An asynchronous node that generates and executes a SQL query.
    """
    step_text = state.get("request", "")
    try:
        # Use the async 'ainvoke' method for the agent call
        user = state.get("user")
        out = await DatabaseAgent.ainvoke({"request": step_text, "user": user})
        query = out.query
        results = []
        
        try:
            conn = await asyncpg.connect(
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
                database=os.getenv("DB_NAME"),
                host="localhost",
                port=5432,
            )
            rows = await conn.fetch(query)
            if rows:
                df = pd.DataFrame(rows)
                results = df.to_dict(orient="records")
            else:
                results = []
            await conn.close()

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