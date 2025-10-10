import pandas as pd
import aiosqlite  # Import the async library
import asyncio
from typing import TypedDict
from langgraph.graph import StateGraph, END, START
from agents import DatabaseAgent

# --- State Definition (Unchanged) ---
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
        # 1. Use the async 'ainvoke' method for the agent call
        out = await DatabaseAgent.ainvoke({"request": step_text, "user": "1"})
        query = out.query
        results = []

        # 2. Use 'aiosqlite' for non-blocking database operations
        db_path = r"D:\Grad Project\Multi-Agent System\Grad\data\database.db"
        try:
            async with aiosqlite.connect(db_path) as conn:
                async with conn.execute(query) as cursor:
                    # Fetch results and column names to build a DataFrame
                    rows = await cursor.fetchall()
                    columns = [description[0] for description in cursor.description]
                    df = pd.DataFrame(rows, columns=columns)
                    results = df.to_dict(orient="records")
                    # print(results)
        except Exception as e:
            results = f"Error Executing Query: {str(e)}"
        
        return {"result": {"step": step_text, "query": query, "data": results}}

    except Exception as e:
        return {"result": {"step": step_text, "query": None, "data": f"Agent Error: {str(e)}"}}

# --- Graph Building (Unchanged) ---
builder = StateGraph(DatabaseAgentState)
builder.add_node("database_agent", database_agent) # LangGraph handles both sync and async nodes
builder.add_edge(START, "database_agent")
builder.add_edge("database_agent", END)

database_agent_super_agent = builder.compile()