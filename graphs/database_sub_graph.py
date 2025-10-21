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
    edit: bool


async def database_agent(state: DatabaseAgentState) -> dict:
    """
    An asynchronous node that generates and executes a SQL query.
    """

    user = state.get("user_id")
    step_text = state.get("request", "")
    
    print('--- Database Agent State ---')
    print(user)
    print(step_text)
    out = await DatabaseAgent.ainvoke({"request": step_text, "user_id": user})
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
                    # Convert asyncpg.Record -> dict to preserve column names
                    results = [dict(r) for r in rows]
                else:
                    results = []
                await conn.close()

            except Exception as e:
                results = f"Error Executing Query: {str(e)}"
            return {"result": {"step": step_text, "query": query, "data": results}, "edit": False}

        except Exception as e:
            return {"result": {"step": step_text, "query": None, "data": f"Agent Error: {str(e)}"}, "edit": False}
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
            return {"result": {"step": step_text, "query": query, "data": "Edit Query Executed Successfully"}, "edit": True}
        except Exception as e:
            return {"result": {"step": step_text, "query": query, "data": f"Error Executing Edit Query: {str(e)}"}, "edit": True}


builder = StateGraph(DatabaseAgentState)
builder.add_node("database_agent", database_agent)
builder.add_edge(START, "database_agent")
builder.add_edge("database_agent", END)

database_agent_super_agent = builder.compile()