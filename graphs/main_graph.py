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


class OrchestratorState(TypedDict):
    """State for the orchestrator graph."""
    user_id: str
    user_name: str
    user_message: str
    agent_result: dict
    sender: str
    analysis: str
    routing_decision: str
    routing_message: str # message from the router till the agent what to do
    final_output: str  # Final message from PersonalAssistant
    message: str  # Plain text message from PersonalAssistant
    has_data: bool  # True if data is available to display, False if only message
    data: dict  # Actual data to display (if has_data is True)
    is_awaiting_data: bool  # True if waiting for data from agent to embed in next round, False if table ready to display


# Single assistant instance (previous behavior)
personal_assistant = None


def personal_assistant_orchestrator(state: OrchestratorState) -> dict:
    """PersonalAssistant uses LLM to decide routing and generate message."""
    global personal_assistant
    if personal_assistant is None:
        personal_assistant = PersonalAssistant(user_id=state.get("user_id", "default"), user_name=state.get("user_name", "User"))
    
    user_message = state.get("user_message", "")
    user_name = state.get("user_name", "User")
    
    # System prompt for routing decision
    system_prompt = """
    You are a Personal Assistant's routing system. Your job is to:
    1. Analyze the user's request
    2. Decide which agent should handle it:
        - "database_agent": For queries about transactions, spending, budget, income, account data, balance, history
        - "behaviour_analyst": For requests about analysis, trends, recommendations, insights, patterns, comparisons
        - "personal_assistant": For general chat that doesn't need any agent
    3. Generate a message telling the agent/assistant what to do
    
    Be concise and helpful. The message should acknowledge the user's request and explain what action you're taking.
    """

    user_prompt = f"""
    User: {user_message} User Name: {user_name}
    Please analyze this request and decide which agent should handle it. and the message to be sent to the selected agent.
    """
    
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", user_prompt)
    ])
    formatted_prompt = prompt_template.format_prompt()
    
    routing_output = gpt_oss_llm.with_structured_output(RoutingDecision).invoke(formatted_prompt)
        
    agent = routing_output.agent
    message = routing_output.message

    return {
        "routing_decision": agent,
        "routing_message": message
    }


async def database_agent_node(state: OrchestratorState) -> dict:
    """Execute Database Agent and return results asynchronously."""
    db_state = {
        "request": state.get("routing_message"),
        "user_id": state.get("user_id"),
    }
    
    result = await database_agent_super_agent.ainvoke(db_state)
    agent_result = result.get("result", {})
    data = agent_result.get("data", [])
    edit = result.get("edit", False)
    return {
        "is_awaiting_data": not edit,
        "data": data,
        "routing_decision": "database_agent"
    }


async def behaviour_analyst_node(state: OrchestratorState) -> dict:
    """Execute Behaviour Analyst and return results asynchronously."""
    
    analysis_state = {
        "request": state.get("routing_message"),
        "user_id": state.get("user_id")
    }
    
    result = await behaviour_analyst_super_agent.ainvoke(analysis_state, {"recursion_limit": 500})
    result = result.get("analysis", {})
    return {
        "analysis": result,
        "routing_decision": "behaviour_analyst",
        "is_awaiting_data": False,
    }


def personal_assistant_response(state: OrchestratorState) -> dict:
    """PersonalAssistant generates final response using memory and context."""
    global personal_assistant
    if personal_assistant is None:
        personal_assistant = PersonalAssistant(user_id=state.get("user_id", "default"), user_name=state.get("user_name", "User"))
    routing_decision = state.get("routing_decision", "personal_assistant")
    routing_message = state.get("routing_message", "")
    is_awaiting_data = state.get("is_awaiting_data", False)
    if routing_decision == "database_agent":
        if is_awaiting_data:
            confirmation_prompt = f"The user ({state.get('user_name','User')}) asked: {state.get('user_message')}. Give a very brief one-sentence confirmation that you're showing them the results."
            confirmation = personal_assistant.invoke(confirmation_prompt, context={
                                                        "routing_decision": routing_decision,
                                                        "routing_message": routing_message
                                                    })
            return {
                "has_data": True,
                "data": state.get("data", []),
                "final_output": confirmation.get("response","no confirmation")
            }
        user_name = state.get("user_name", "User")
        confirmation = personal_assistant.invoke(confirmation_prompt, context={
            "routing_decision": routing_decision,
            "routing_message": routing_message
        })
        return {
            "final_output": confirmation.get("response","no confirmation"),
            "data": [],
            "has_data": False
        }
    elif routing_decision == "behaviour_analyst":
        analysis = state.get("analysis", {})
        context = {
            "analysis": analysis,
            "routing_decision": routing_decision,
            "routing_message": routing_message,
            "type": state.get("user_message")
        }    
        response = personal_assistant.invoke(state.get("user_message",""), context=context).get("response","no response")
        return {
            "final_output": response,
            "data": [],
            "has_data": False
        }
    
    context = {
            "user_message": state.get("user_message"),
            "routing_message": routing_message,
            "type": state.get("user_message")
    }
    
    response = personal_assistant.invoke(state.get("user_message",""), context=context)
    return {
        "final_output": response.get("response","no response"),
        "data": [],
        "has_data": False
    }


def route_to_next_step(state: OrchestratorState) -> str:
    """Route based on PersonalAssistant decision."""
    routing_decision = state.get("routing_decision", "")
    if routing_decision == "database_agent":
        return "database_agent"
    elif routing_decision == "behaviour_analyst":
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