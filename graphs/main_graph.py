"""
Main Orchestrator Graph - PersonalAssistant as the Orchestrator

PersonalAssistant orchestrates the flow:
- Routes requests to Database Agent or Behaviour Analyst
- Handles memory and context
- Generates final response using PersonalAssistant
"""

import asyncio
from typing import TypedDict
from langgraph.graph import StateGraph, END, START
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from graphs.database_sub_graph import database_agent_super_agent
from graphs.behaviour_analyst_sub_graph import behaviour_analyst_super_agent
from agents.personal_assistant import PersonalAssistant
from LLMs.azure_models import gpt_oss_llm


class RoutingDecision(BaseModel):
    """Structured output for routing decision."""
    agent: str = Field(..., description="Which agent to route to: 'database_agent', 'behaviour_analyst', or 'conversation'")
    message: str = Field(..., description="Message to send to the user about this routing decision")
    reasoning: str = Field(..., description="Brief explanation of why this agent was chosen")


class OrchestratorState(TypedDict):
    """State for the orchestrator graph."""
    user_id: str
    user_name: str
    user_message: str
    next_step: str
    agent_result: dict
    routing_decision: str
    routing_message: str
    message: str  # Plain text message from PersonalAssistant
    has_data: bool  # True if data is available to display, False if only message
    data: dict  # Actual data to display (if has_data is True)
    is_awaiting_data: bool  # True if waiting for data from agent to embed in next round, False if table ready to display


# Single assistant instance (previous behavior)
personal_assistant = None


def personal_assistant_orchestrator(state: OrchestratorState) -> dict:
    """PersonalAssistant uses LLM to decide routing and generate message."""
    print("===> (Node) Personal Assistant Orchestrator <===")
    print(state)

    global personal_assistant
    if personal_assistant is None:
        personal_assistant = PersonalAssistant(user_id=state.get("user_id", "default"), user_name=state.get("user_name", "User"))
    
    user_message = state.get("user_message", "")
    user_name = state.get("user_name", "User")
    
    # System prompt for routing decision
    system_prompt = """You are a Personal Assistant's routing system. Your job is to:

1. Analyze the user's request
2. Decide which agent should handle it:
    - "database_agent": For queries about transactions, spending, budget, income, account data, balance, history
    - "behaviour_analyst": For requests about analysis, trends, recommendations, insights, patterns, comparisons
    - "conversation": For general chat that doesn't need any agent
3. Generate a friendly message to the user explaining what you'll do

Be concise and helpful. The message should acknowledge the user's request and explain what action you're taking."""

    user_prompt = f"""User: {user_message}
User Name: {user_name}

Please analyze this request and decide which agent should handle it. Respond with a routing decision and a message to send to the user."""

    # Build prompt
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", user_prompt)
    ])
    
    formatted_prompt = prompt_template.format_prompt()
    
    routing_output = gpt_oss_llm.with_structured_output(RoutingDecision).invoke(formatted_prompt)
        
    agent = routing_output.agent
    message = routing_output.message
    reasoning = routing_output.reasoning
    
    return {
        "next_step": agent,
        "routing_decision": agent,
        "routing_message": message
    }


async def database_agent_node(state: OrchestratorState) -> dict:
    """Execute Database Agent and return results asynchronously."""
    db_state = {
        "request": state.get("user_message"),
        "user_id": state.get("user_id"),
    }
    
    result = await database_agent_super_agent.ainvoke(db_state)
    agent_result = result.get("result", {})
    data = agent_result.get("data", [])
    
    # is_awaiting_data = True if:
    # 1. Data is a list with records (SELECT query results)
    # 2. Data is a success/error message string (INSERT/UPDATE/DELETE results)
    is_table = isinstance(data, list) and len(data) > 0
    is_message = isinstance(data, str)  # Success or error message from edit query
    
    is_awaiting_data = is_table or is_message
    
    return {
        "agent_result": agent_result,
        "is_awaiting_data": is_awaiting_data,
    }


async def behaviour_analyst_node(state: OrchestratorState) -> dict:
    """Execute Behaviour Analyst and return results asynchronously."""
    analysis_state = {
        "request": state.get("user_message"),
        "data_acquired": [],
        "analysis": "pending",
        "final_output": "pending",
        "message": state.get("user_message"),
        "sender": "personal_assistant",
        "user_id": state.get("user_id")
    }
    
    # Use ainvoke for async execution
    result = await behaviour_analyst_super_agent.ainvoke(analysis_state, {"recursion_limit": 500})
    result = result.get("analysis", {})
    
    is_awaiting_data = False  # Always returns data to embed for analysis
    
    return {
        "agent_result": result,
        "is_awaiting_data": is_awaiting_data,
    }


def personal_assistant_response(state: OrchestratorState) -> dict:
    """PersonalAssistant generates final response using memory and context."""
    global personal_assistant
    if personal_assistant is None:
        personal_assistant = PersonalAssistant(user_id=state.get("user_id", "default"), user_name=state.get("user_name", "User"))
    
    # Get agent results if any
    agent_result = state.get("agent_result", {})
    routing_decision = state.get("routing_decision", "conversation")
    routing_message = state.get("routing_message", "")
    is_awaiting_data = state.get("is_awaiting_data", False)
    
    # If there IS data from agent (is_awaiting_data = True), display it with confirmation
    if is_awaiting_data and agent_result:
        data = agent_result.get("data", [])
        
        # Handle table data (list of records) - ONLY set has_data=True for this
        if isinstance(data, list) and len(data) > 0:
            # Format as simple table
            import pandas as pd
            df = pd.DataFrame(data)
            table_str = df.to_string(index=False)
            
            # Get a confirmation comment from PersonalAssistant
            user_name = state.get("user_name", "User")
            confirmation_prompt = f"The user ({user_name}) asked: {state.get('user_message')}. Give a very brief one-sentence confirmation that you're showing them the results."
            
            confirmation = personal_assistant.invoke(confirmation_prompt, context={})
            confirmation_text = confirmation.get("response", "Here are your results:")
            
            final_message = f"{confirmation_text}\n\n{table_str}"
            
            if routing_message:
                final_message += f"\n\n[{routing_message}]"
            
            return {
                "message": confirmation_text,
                "has_data": True,  # TRUE: tabular data exists
                "data": data,
            }
        
        # Handle message data (string from edit/insert/delete operations) - NO tabular data
        elif isinstance(data, str):
            # Get a confirmation comment from PersonalAssistant
            user_name = state.get("user_name", "User")
            confirmation_prompt = f"The user ({user_name}) asked: {state.get('user_message')}. The result was: {data}. Give a very brief one-sentence confirmation/summary of what happened."
            
            confirmation = personal_assistant.invoke(confirmation_prompt, context={})
            confirmation_text = confirmation.get("response", data)
            
            final_message = confirmation_text
            
            if routing_message:
                final_message += f"\n\n[{routing_message}]"
            
            return {
                "message": confirmation_text,
                "has_data": False,  # FALSE: only message/text, no tabular data
                "data": None,
            }
    
    # For conversation (no external data needed) or text responses
    # Build context for response
    context = {
        "agent_result": agent_result,
        "routing_decision": routing_decision,
        "routing_message": routing_message,
        "type": state.get("user_message")
    }
    
    # PersonalAssistant generates response with memory
    response = personal_assistant.invoke(state.get("user_message"), context=context)
    
    # Build final response
    final_message = response.get("response", "")
    response_text = final_message
    
    # Add routing message to output
    if routing_decision != "conversation" and routing_message:
        final_message += f"\n\n[{routing_message}]"
    
    return {
        "message": response_text,
        "has_data": False,  # FALSE: no tabular data
        "data": None,
    }


def route_after_agent(state: OrchestratorState) -> str:
    """Route from agent execution to PersonalAssistant response."""
    return "personal_assistant_response"


def route_to_next_step(state: OrchestratorState) -> str:
    """Route based on PersonalAssistant decision."""
    next_step = state.get("next_step", "conversation")
    
    if next_step == "database_agent":
        return "database_agent"
    elif next_step == "behaviour_analyst":
        return "behaviour_analyst"
    else:
        return "personal_assistant_response"


builder = StateGraph(OrchestratorState)

builder.add_node("personal_assistant_orchestrator", personal_assistant_orchestrator)
builder.add_node("database_agent", database_agent_node)
builder.add_node("behaviour_analyst", behaviour_analyst_node)
builder.add_node("personal_assistant_response", personal_assistant_response)

builder.add_edge(START, "personal_assistant_orchestrator")


builder.add_conditional_edges(
    "personal_assistant_orchestrator",
    route_to_next_step,
    {
        "database_agent": "database_agent",
        "behaviour_analyst": "behaviour_analyst",
        "personal_assistant_response": "personal_assistant_response",
    }
)

builder.add_edge("database_agent", "personal_assistant_response")
builder.add_edge("behaviour_analyst", "personal_assistant_response")
builder.add_edge("personal_assistant_response", END)
main_orchestrator_graph = builder.compile()