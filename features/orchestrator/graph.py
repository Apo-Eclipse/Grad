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
from features.database_agent.graph import database_agent_super_agent
from features.behaviour_analyst.graph import behaviour_analyst_super_agent
from features.personal_assistant.agent import invoke_personal_assistant
from features.crud.conversations.service import get_conversation_summary
from core.llm_providers.digital_ocean import gpt_oss_120b_digital_ocean
from langchain_core.messages import BaseMessage
import json

from features.crud.budgets.service import fetch_active_budgets


class RoutingDecision(BaseModel):
    """Structured output for routing decision."""

    agent: str = Field(
        ...,
        description="Which agent to route to: 'database_agent', 'behaviour_analyst', or 'personal_assistant_response'",
    )
    message: str = Field(
        ..., description="Message to send to the user about this routing decision"
    )


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
    routing_message: str  # message from the router till the agent what to do
    final_output: str  # Final message from PersonalAssistant
    message: str  # Plain text message from PersonalAssistant
    has_data: bool  # True if data is available to display, False if only message
    data: dict  # Actual data to display (if has_data is True)
    is_awaiting_data: bool  # True if waiting for data from agent to embed in next round, False if table ready to display
    agents_used: (
        str  # Track which agent was called: 'database_agent', 'behaviour_analyst', etc.
    )


def parse_output(message: BaseMessage | str) -> RoutingDecision | None:
    text = message.content if isinstance(message, BaseMessage) else message
    text = text.replace("```json", "").replace("```", "").strip()
    try:
        data = json.loads(text)
        return RoutingDecision(**data)
    except Exception as e:
        print(f"Parsing error: {e}")
        print(f"Raw Output: {text}")
        return None

def personal_assistant_orchestrator(state: OrchestratorState) -> dict:
    """PersonalAssistant uses LLM to decide routing and generate message."""

    conversation_id = state.get("conversation_id", "")
    user_id = state.get("user_id", "default")
    user_name = state.get("user_name", "User")

    # Fetch active budgets directly
    try:
        budgets = fetch_active_budgets(int(user_id)) if str(user_id).isdigit() else []
        if budgets:
            available_budgets = ", ".join(
                [f"{b['budget_name']} (ID: {b['budget_id']})" for b in budgets]
            )
        else:
            available_budgets = "No active budgets found."
    except Exception:
        available_budgets = "Error fetching budgets."

    # 1. Fetch Memory Externally (Stateless Pattern)
    conversation_memory_str = (
        get_conversation_summary(int(conversation_id))
        if str(conversation_id).isdigit()
        else "No history."
    )

    print("conversation_memory_str", conversation_memory_str)

    user_message = state.get("user_message", "")

    # System prompt for routing decision
    system_prompt = """
    last conversations: {conversation_memory_str}
    Available Budgets: {available_budgets}

    You are the Personal Assistant Orchestrator (Router).

    Your responsibility is to:
    1) Analyze the user's message.
    2) Decide which agent should handle it.
    3) Output a SINGLE valid JSON object with EXACTLY two keys:
    - "agent": one of ["database_agent", "behaviour_analyst", "personal_assistant_response"]
    - "message": a clear, specific instruction for the chosen agent.

    --------------------------------------------------
    CRITICAL OUTPUT RULES
    --------------------------------------------------
    - Return ONLY valid JSON.
    - Do NOT include markdown, comments, or explanations.
    - Use double quotes and valid JSON syntax.
    - Do NOT add extra keys.
    - Do NOT invent data or assumptions.

    --------------------------------------------------
    AVAILABLE AGENTS
    --------------------------------------------------

    1) "database_agent"
    - STRICTLY READ-ONLY.
    - Used ONLY for retrieving or aggregating existing data.
    - NEVER performs insert, update, or delete operations.

    2) "behaviour_analyst"
    - Used for insights, trends, patterns, comparisons, explanations, and recommendations.
    - Answers questions that ask WHY something happened or HOW to improve.

    3) "personal_assistant_response"
    - Used for general chatting, clarifications, explanations, and redirection.
    - NEVER reads from the database.
    - NEVER writes to the database.
    - ONLY talks to the user.

    --------------------------------------------------
    ROUTING RULES
    --------------------------------------------------

    A) Route to "database_agent" if the user asks for factual data retrieval, such as:
    - Spending totals or balances
    - Transaction history
    - Budget usage or limits
    - Income totals
    - Time-based queries (current month, last month, last year)

    Message MUST specify:
    - Time window (explicit or inferred)
    - Budget/category if mentioned
    - Aggregation required (e.g., total, grouped by month/category)
    - **PRIVACY FILTER**: "Do NOT return internal IDs (e.g., id, budget_id, user_id). Select only human-readable columns (e.g., budget_name, date, amount, description)."

    --------------------------------------------------

    B) Route to "behaviour_analyst" if the user asks for:
    - Reasons ("why am I overspending?")
    - Trends or patterns
    - Comparisons between periods
    - Recommendations or behavioral insights

    Message MUST specify:
    - The analytical goal
    - The time window(s) to analyze
    - If critical info is missing, instruct the analyst to ask ONE clarification question.

    --------------------------------------------------

    C) Route to "personal_assistant_response" if:
    - The user is greeting or chatting
    - The user asks about capabilities or help
    - The request is ambiguous and needs clarification
    - The user expresses emotions or concerns
    - The user requests any create/update/delete action (write operations not supported in this graph)

    IMPORTANT:
    - The assistant must NEVER claim that data was saved or changed.

    =======================================================================
    EXAMPLES (ONE PER AGENT)
    =======================================================================
    Example 1 — Database Agent  
    User: "How much did I spend on Food last month?"

    output:

    "agent": "database_agent", 
    "message": "Compute total spending for the Food category for last month and return the total. Do NOT return IDs." 
    =======================================================================
    Example 2 — Behaviour Analyst  
    User: "Why am I overspending on Dining Out?"

    output:

    "agent": "behaviour_analyst",
    "message": "Analyze Dining Out spending for the current month versus last month; explain the reasons and provide recommendations." 
    =======================================================================
    Example 3 — General Chat  
    User: "I feel like I’m always broke"
    
    output:

    "agent": "personal_assistant_response", 
    "message": "Respond empathetically and ask if the user would like help reviewing spending or getting advice." 
    =======================================================================
    """

    user_prompt = """
    User: {user_message} User Name: {user_name}
    Please analyze this request and decide which agent should handle it. and the message to be sent to the selected agent.
    """

    prompt_template = ChatPromptTemplate.from_messages(
        [("system", system_prompt), ("human", user_prompt)]
    )
    formatted_prompt = {
            "conversation_memory_str": conversation_memory_str,
            "available_budgets": available_budgets,
            "user_message": user_message,
            "user_name": user_name,
    }
    model = prompt_template | gpt_oss_120b_digital_ocean | parse_output
    routing_output = model.invoke(formatted_prompt)
    if routing_output is None:
        return {
            "routing_decision": "personal_assistant_response",
            "routing_message": "Respond to the user directly.",
        }
    agent = routing_output.agent
    message = routing_output.message
    print("agent", agent)
    print("message", message)
    return {"routing_decision": agent, "routing_message": message}


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
            database_agent_super_agent.ainvoke(db_state), timeout=20.0
        )
        agent_result = result.get("result", {})
        data = agent_result.get("data", [])
        edit = result.get("edit", False)
        return {
            "is_awaiting_data": not edit,
            "data": data,
            "routing_decision": "database_agent",
            "agents_used": "database_agent",
        }
    except asyncio.TimeoutError:
        print(f"[Database Agent] Timeout after 10 seconds while handling request")
        return {
            "is_awaiting_data": False,
            "data": [],
            "routing_decision": "database_agent",
            "agents_used": "database_agent",
        }
    except Exception as e:
        print(f"[Database Agent] Error while handling request: {e}")
        return {
            "is_awaiting_data": False,
            "data": [],
            "routing_decision": "database_agent",
            "agents_used": "database_agent",
        }


async def behaviour_analyst_node(state: OrchestratorState) -> dict:
    """Execute Behaviour Analyst and return results asynchronously."""

    analysis_state = {
        "request": state.get("routing_message"),
        "user_id": state.get("user_id"),
    }

    result = await behaviour_analyst_super_agent.ainvoke(
        analysis_state, {"recursion_limit": 100}
    )
    result = result.get("analysis", {})
    return {
        "analysis": result,
        "routing_decision": "behaviour_analyst",
        "is_awaiting_data": False,
        "agents_used": "behaviour_analyst",
    }


def personal_assistant_response(state: OrchestratorState) -> dict:
    """PersonalAssistant generates final response using memory and context."""

    conversation_id = state.get("conversation_id", "")
    user_id = state.get("user_id", "default")
    user_name = state.get("user_name", "User")

    # 1. Fetch Memory Externally
    conversation_memory_str = (
        get_conversation_summary(int(conversation_id))
        if str(conversation_id).isdigit()
        else "No history."
    )

    routing_decision = state.get("routing_decision", "personal_assistant")
    routing_message = state.get("routing_message", "")
    is_awaiting_data = state.get("is_awaiting_data", False)
    agents_used = state.get("agents_used", "")  # Preserve agents_used from state

    if routing_decision == "database_agent":
        if is_awaiting_data:
            confirmation_prompt = f"The user ({state.get('user_name', 'User')}) asked: {state.get('user_message')}. Give a very brief one-sentence confirmation that you're showing them the results."
            confirmation = invoke_personal_assistant(
                confirmation_prompt,
                conversation_history=conversation_memory_str,
                context={
                    "routing_decision": routing_decision,
                    "routing_message": routing_message,
                },
                user_id=user_id,
                user_name=user_name,
            )
            return {
                "has_data": True,
                "data": state.get("data", []),
                "final_output": confirmation.get("response", "no confirmation"),
                "agents_used": agents_used,  # Preserve agents_used
            }
        confirmation_prompt = f"The user ({state.get('user_name', 'User')}) asked: {state.get('user_message')}. Give a very brief one-sentence confirmation."
        confirmation = invoke_personal_assistant(
            confirmation_prompt,
            conversation_history=conversation_memory_str,
            context={
                "routing_decision": routing_decision,
                "routing_message": routing_message,
            },
            user_id=user_id,
            user_name=user_name,
        )
        return {
            "final_output": confirmation.get("response", "no confirmation"),
            "data": [],
            "has_data": False,
            "agents_used": agents_used,  # Preserve agents_used
        }
    elif routing_decision == "behaviour_analyst":
        analysis = state.get("analysis", {})
        context = {
            "analysis": analysis,
            "routing_decision": routing_decision,
            "routing_message": routing_message,
            "type": state.get("user_message"),
        }
        response = invoke_personal_assistant(
            state.get("user_message", ""),
            conversation_history=conversation_memory_str,
            context=context,
            user_id=user_id,
            user_name=user_name,
        ).get("response", "no response")
        return {
            "final_output": response,
            "data": [],
            "has_data": False,
            "agents_used": agents_used,  # Preserve agents_used
        }

    context = {
        "user_message": state.get("user_message"),
        "routing_message": routing_message,
        "type": state.get("user_message"),
    }

    response = invoke_personal_assistant(
        state.get("user_message", ""),
        conversation_history=conversation_memory_str,
        context=context,
        user_id=user_id,
        user_name=user_name,
    )
    return {
        "final_output": response.get("response", "no response"),
        "data": [],
        "has_data": False,
        "agents_used": agents_used,  # Preserve agents_used
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
    },
)

builder.add_edge("database_agent", "personal_assistant_response")
builder.add_edge("behaviour_analyst", "personal_assistant_response")
builder.add_edge("personal_assistant_response", END)
main_orchestrator_graph = builder.compile()
