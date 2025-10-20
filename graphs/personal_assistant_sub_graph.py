"""
Personal Assistant SubGraph

Integrates the Personal Assistant agent into the main multi-agent workflow.
Provides memory-aware conversational interaction capabilities.
"""

from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, END, START
import csv
from agents.personal_assistant.assistant import PersonalAssistant


class PersonalAssistantGraphState(TypedDict):
    """State definition for Personal Assistant subgraph."""
    user_id: str
    user_name: str
    user_message: str
    response: str
    context: Dict[str, Any]
    memory_stats: Dict[str, Any]
    message: str
    next_step: str
    steps: List[str]


def add_to_logs(sender: str, receiver: str, message: str):
    """Append a log entry to the CSV file."""
    try:
        with open(r"D:\projects\Multi-Agent System\data\logs.csv", mode='a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow([sender, receiver, str(message)])
    except Exception as e:
        print(f"Error writing to logs: {e}")


def personal_assistant_node(state: PersonalAssistantGraphState) -> dict:
    """
    Main personal assistant processing node.
    Handles user interaction with memory management.
    """
    print("===> (Node) Personal Assistant Processing <===")
    user_id = state.get("user_id", "default_user")
    user_name = state.get("user_name", "User")
    user_message = state.get("user_message", "")

    try:
        # Create or retrieve assistant
        assistant = PersonalAssistant(user_id, user_name)

        # Process the message
        result = assistant.invoke(user_message, context=state.get("context"))

        # Get memory statistics
        memory_stats = assistant.get_memory_summary()

        response = result.get("response", "")
        message = response

        add_to_logs("personal_assistant", "orchestrator", message)

        return {
            "response": response,
            "message": message,
            "memory_stats": memory_stats,
            "next_step": "end",
            "steps": [*state.get("steps", []), "personal_assistant_processed"]
        }

    except Exception as e:
        error_message = f"Error in personal assistant: {str(e)}"
        print(error_message)
        add_to_logs("personal_assistant", "orchestrator", error_message)

        return {
            "response": f"I encountered an error: {str(e)}. Please try again.",
            "message": error_message,
            "next_step": "end"
        }


def create_personal_assistant_subgraph():
    """
    Create the Personal Assistant subgraph.

    Returns:
        Compiled StateGraph for personal assistant operations
    """
    workflow = StateGraph(PersonalAssistantGraphState)

    # Add nodes
    workflow.add_node("personal_assistant", personal_assistant_node)

    # Define flow
    workflow.add_edge(START, "personal_assistant")
    workflow.add_edge("personal_assistant", END)

    return workflow.compile()


# Export the compiled agent
personal_assistant_subgraph = create_personal_assistant_subgraph()
