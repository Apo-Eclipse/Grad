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
    user_id: object


# --- ASYNC Node Definition ---
async def database_agent(state: DatabaseAgentState) -> dict:
    """
    An asynchronous node that generates and executes a SQL query.
    """
    # Compact debug to observe what's coming from main graph without dumping huge payloads

    try:
        print("[database_agent] keys:", list(state.keys()))
        print("[database_agent] request:", state.get("request"))
        print("[database_agent] user_id:", state.get("user") or state.get("user_id"))
    except Exception:
        pass

    user = state.get("user") or state.get("user_id")
    step_text = state.get("request", "")

    out = await DatabaseAgent.ainvoke({"request": step_text, "user": user})
    query = out.query
    edit = out.edit

    if not edit:
        try:
            results = []
            try:
                conn = await asyncpg.connect(
                    user=os.getenv("DB_USER"),
                    password=os.getenv("DB_PASSWORD"),
                    database=os.getenv("DB_NAME"),
                    host=os.getenv("DB_HOST"),
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
    else:
        try:
            conn = await asyncpg.connect(
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
                database=os.getenv("DB_NAME"),
                host=os.getenv("DB_HOST"),
                port=5432,
            )
            await conn.execute(query)
            await conn.close()
            return {"result": {"step": step_text, "query": query, "data": "Edit Query Executed Successfully"}}
        except Exception as e:
            return {"result": {"step": step_text, "query": query, "data": f"Error Executing Edit Query: {str(e)}"}}


builder = StateGraph(DatabaseAgentState)
builder.add_node("database_agent", database_agent)
builder.add_edge(START, "database_agent")
builder.add_edge("database_agent", END)

database_agent_super_agent = builder.compile()