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
from agents.personal_assistant.memory_manager import ConversationMemory
from LLMs.azure_models import gpt_oss_llm


class RoutingDecision(BaseModel):
    """Structured output for routing decision."""
    agent: str = Field(..., description="Which agent to route to: 'database_agent', 'behaviour_analyst', or 'conversation'")
    message: str = Field(..., description="Message to send to the user about this routing decision")


from api.personal_assistant_api.db_retrieval import fetch_active_budgets

class OrchestratorState(TypedDict):
    """State for the orchestrator graph."""
    user_id: str
    conversation_id: str
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
    agents_used: str  # Track which agent was called: 'database_agent', 'behaviour_analyst', etc.


def personal_assistant_orchestrator(state: OrchestratorState) -> dict:
    """PersonalAssistant uses LLM to decide routing and generate message."""
    
    conversation_id = state.get("conversation_id", "")
    user_id = state.get("user_id", "default")
    user_name = state.get("user_name", "User")
    
    # Fetch active budgets directly
    try:
        budgets = fetch_active_budgets(int(user_id)) if str(user_id).isdigit() else []
        if budgets:
            available_budgets = ", ".join([f"{b['budget_name']} (ID: {b['budget_id']})" for b in budgets])
        else:
            available_budgets = "No active budgets found."
    except Exception:
        available_budgets = "Error fetching budgets."
    
    # 1. Fetch Memory Externally (Stateless Pattern)
    memory = ConversationMemory(user_id=user_id, conversation_id=conversation_id)
    memory.retrieve_conversation(conversation_id)
    conversation_memory_str = memory.get_context_summary()
    
    user_message = state.get("user_message", "")
    
    # System prompt for routing decision
    system_prompt = f"""
    last conversations : {conversation_memory_str}
    
    Available Budgets: {available_budgets}
    
    You are a Personal Assistant's routing system. Your job is to:
    1. Analyze the user's request
    2. Decide which agent should handle it:
        - "database_agent": For queries about transactions, spending, budget, income, account data, balance, history
        - "behaviour_analyst": For requests about analysis, trends, recommendations, insights, patterns, comparisons
        - "personal_assistant": For general chat that doesn't need any agent OR if data is missing for a transaction.
    3. Generate a message telling the agent/assistant what to do, the message should be clear and specific and.
    4. If the user request is related to the memory or previous conversations, when generating the message, you must include relevant context from the conversation history to help the agent understand the user's needs better.
    
    CRITICAL RULE FOR ADDING TRANSACTIONS:
    - If the user wants to ADD a transaction, you MUST check if they provided:
      a) The Amount
      b) The Category (which must match one of the 'Available Budgets' above)
    - IF ANY of these are missing or the category is ambiguous/invalid:
      - Route to "personal_assistant"
      - Message: "Ask the user to provide the missing [Amount/Category]. List the available budgets if the category was invalid."
    - ONLY route to "database_agent" if both Amount and a Valid Category are present.
    - **IMPORTANT**: When routing to "database_agent", you MUST resolve the category name to its 'ID' from the Available Budgets list. Include the 'budget_id' explicitly in the message.
      - Example: "Add transaction of 50 for Food (budget_id 1)..."

    For example:
    
    Assistant: The most recent analysis you requested was about your budget category "Dining Out" for last month.
    User: "Base on my last request i want analysis of the same budget category"
    Message to agent: "Please analyze the budget category 'Dining Out' for last month and provide insights based on that."

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
    routing_message = state.get("routing_message") or ""
    user_message = state.get("user_message") or ""

    # Feed the database agent a full request that always includes the user's ask.
    if routing_message and user_message:
        db_request = f"User ask: {user_message}\nInstruction: {routing_message}"
    elif routing_message:
        db_request = routing_message
    else:
        db_request = user_message

    db_state = {
        "request": db_request.strip(),
        "user_id": state.get("user_id"),
    }
    try:
        result = await asyncio.wait_for(
            database_agent_super_agent.ainvoke(db_state),
            timeout=20.0
        )
        agent_result = result.get("result", {})
        data = agent_result.get("data", [])
        edit = result.get("edit", False)
        return {
            "is_awaiting_data": not edit,
            "data": data,
            "routing_decision": "database_agent",
            "agents_used": "database_agent"
        }
    except asyncio.TimeoutError:
        print(f"[Database Agent] Timeout after 10 seconds while handling request")
        return {
            "is_awaiting_data": False,
            "data": [],
            "routing_decision": "database_agent",
            "agents_used": "database_agent"
        }
    except Exception as e:
        print(f"[Database Agent] Error while handling request: {e}")
        return {
            "is_awaiting_data": False,
            "data": [],
            "routing_decision": "database_agent",
            "agents_used": "database_agent"
        }


async def behaviour_analyst_node(state: OrchestratorState) -> dict:
    """Execute Behaviour Analyst and return results asynchronously."""
    
    analysis_state = {
        "request": state.get("routing_message"),
        "user_id": state.get("user_id")
    }
    
    result = await behaviour_analyst_super_agent.ainvoke(analysis_state, {"recursion_limit": 100})
    result = result.get("analysis", {})
    return {
        "analysis": result,
        "routing_decision": "behaviour_analyst",
        "is_awaiting_data": False,
        "agents_used": "behaviour_analyst"
    }


def personal_assistant_response(state: OrchestratorState) -> dict:
    """PersonalAssistant generates final response using memory and context."""
    
    conversation_id = state.get("conversation_id", "")
    user_id = state.get("user_id", "default")
    user_name = state.get("user_name", "User")
    
    # 1. Fetch Memory Externally
    memory = ConversationMemory(user_id=user_id, conversation_id=conversation_id)
    memory.retrieve_conversation(conversation_id)
    conversation_memory_str = memory.get_context_summary()
    
    # 2. Instantiate Stateless Assistant
    personal_assistant = PersonalAssistant(
        user_id=user_id,
        conversation_id=conversation_id,
        user_name=user_name
    )
    
    routing_decision = state.get("routing_decision", "personal_assistant")
    routing_message = state.get("routing_message", "")
    is_awaiting_data = state.get("is_awaiting_data", False)
    agents_used = state.get("agents_used", "")  # Preserve agents_used from state
    
    if routing_decision == "database_agent":
        if is_awaiting_data:
            confirmation_prompt = f"The user ({state.get('user_name','User')}) asked: {state.get('user_message')}. Give a very brief one-sentence confirmation that you're showing them the results."
            confirmation = personal_assistant.invoke(confirmation_prompt, conversation_history=conversation_memory_str, context={
                                                        "routing_decision": routing_decision,
                                                        "routing_message": routing_message
                                                    })
            return {
                "has_data": True,
                "data": state.get("data", []),
                "final_output": confirmation.get("response","no confirmation"),
                "agents_used": agents_used  # Preserve agents_used
            }
        confirmation_prompt = f"The user ({state.get('user_name','User')}) asked: {state.get('user_message')}. Give a very brief one-sentence confirmation."
        confirmation = personal_assistant.invoke(confirmation_prompt, conversation_history=conversation_memory_str, context={
            "routing_decision": routing_decision,
            "routing_message": routing_message
        })
        return {
            "final_output": confirmation.get("response","no confirmation"),
            "data": [],
            "has_data": False,
            "agents_used": agents_used  # Preserve agents_used
        }
    elif routing_decision == "behaviour_analyst":
        analysis = state.get("analysis", {})
        context = {
            "analysis": analysis,
            "routing_decision": routing_decision,
            "routing_message": routing_message,
            "type": state.get("user_message")
        }    
        response = personal_assistant.invoke(state.get("user_message",""), conversation_history=conversation_memory_str, context=context).get("response","no response")
        return {
            "final_output": response,
            "data": [],
            "has_data": False,
            "agents_used": agents_used  # Preserve agents_used
        }
    
    context = {
            "user_message": state.get("user_message"),
            "routing_message": routing_message,
            "type": state.get("user_message")
    }
    
    response = personal_assistant.invoke(state.get("user_message",""), conversation_history=conversation_memory_str, context=context)
    return {
        "final_output": response.get("response","no response"),
        "data": [],
        "has_data": False,
        "agents_used": agents_used  # Preserve agents_used
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
