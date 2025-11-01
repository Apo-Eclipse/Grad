import asyncio
from typing import TypedDict, List

from django.db import connection
from langgraph.graph import StateGraph, END, START

from agents import DatabaseAgent
from api.personal_assistant_api.db_retrieval import dictfetchall


def _prepare_select_sql(query: str, *, limit: int = 100) -> str:
    cleaned = (query or "").strip()
    upper = cleaned.upper()
    if not upper.startswith(("SELECT", "WITH")):
        raise ValueError("Only SELECT queries are allowed for data retrieval.")
    if "LIMIT" not in upper:
        cleaned = cleaned.rstrip(";") + f" LIMIT {limit}"
    return cleaned


def _execute_select_query(query: str) -> List[dict]:
    normalized_query = _prepare_select_sql(query)
    with connection.cursor() as cursor:
        cursor.execute(normalized_query)
        return dictfetchall(cursor)


def _execute_modify_query(query: str) -> str:
    cleaned = (query or "").strip()
    upper = cleaned.upper()
    if not upper.startswith(("INSERT", "UPDATE", "DELETE")):
        raise ValueError(
            "Only INSERT, UPDATE, or DELETE queries are allowed for modifications."
        )
    with connection.cursor() as cursor:
        cursor.execute(cleaned)
        rows_affected = cursor.rowcount
    connection.commit()
    return f"Write operation successful. Rows affected: {rows_affected}"


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
            # SELECT query handled directly via Django connection
            try:
                results = await asyncio.to_thread(_execute_select_query, query)
                return {"step": request, "query": query, "data": results, "edit": False}
            except Exception as e:
                return {"step": request, "query": query, "data": f"Database error: {str(e)}", "edit": False}
        else:
            try:
                message = await asyncio.to_thread(_execute_modify_query, query)
                return {"step": request, "query": query, "data": message, "edit": True}
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
