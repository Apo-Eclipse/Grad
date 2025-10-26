import asyncio
import httpx
import os
from typing import TypedDict
from langgraph.graph import StateGraph, END, START
from agents import DatabaseAgent

API_BASE_URL = "http://localhost:8000/api"


class DatabaseAgentState(TypedDict):
    request: str
    result: dict
    user_id: object
    edit: bool


async def execute_single_query(request: str, user_id: object) -> dict:
    """
    Execute a single database query: LLM generation + API execution.
    """
    try:
        # Generate SQL query using LLM        
        out = await asyncio.to_thread(DatabaseAgent.invoke, {"request": request, "user_id": user_id})
        query = out.query
        edit = out.edit
        if not edit:
            # SELECT query
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.post(
                        f"{API_BASE_URL}/database/execute/select",
                        json={"query": query, "params": []},
                    )
                    if response.status_code == 200:
                        data = response.json()
                        if data.get("success"):
                            results = data.get("data", [])
                        else:
                            results = []
                    else:
                        results = []
                
                return {"step": request, "query": query, "data": results, "edit": False}
            except Exception as e:
                print("Error during SELECT query execution:", str(e))  # Debug log for SELECT errors
                return {"step": request, "query": query, "data": f"API Error: {str(e)}", "edit": False}
        else:
            # WRITE query (INSERT, UPDATE, DELETE)
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    response = await client.post(
                        f"{API_BASE_URL}/database/execute/modify",
                        json={"query": query, "params": []},
                    )
                    print("Database API response for WRITE query:", response.json())  # Debug log for WRITE response
                    if response.status_code == 200:
                        data = response.json()
                        if data.get("success"):
                            message = f"Write operation successful. Rows affected: {data.get('rows_affected', 0)}"
                        else:
                            message = f"Write operation failed: {data.get('error', 'Unknown error')}"
                    else:
                        message = f"API error: HTTP {response.status_code}"
                
            except Exception as e:
                return {"step": request, "query": query, "data": f"Error Executing Edit Query: {str(e)}", "edit": True}
    
    except Exception as e:
        return {"step": request, "query": None, "data": f"LLM Error: {str(e)}", "edit": False}


async def database_agent(state: DatabaseAgentState) -> dict:
    """
    An asynchronous node that generates and executes a SQL query.
    This processes a single request (used when called from behaviour_analyst_sub_graph).
    """
    user = state.get("user_id")
    step_text = state.get("request", "")
    
    result = await execute_single_query(step_text, user)
    return {"result": result, "edit": result.get("edit", False)}


builder = StateGraph(DatabaseAgentState)
builder.add_node("database_agent", database_agent)
builder.add_edge(START, "database_agent")
builder.add_edge("database_agent", END)

database_agent_super_agent = builder.compile()
