"""
Personal Assistant Agent Module

This module provides a personal assistant agent with memory management capabilities.

The agent can:
- Interact with users with natural conversation
- Maintain conversation history and context
- Provide personalized responses based on history
- Work with the orchestrator in main_graph.py for routing
"""

from .memory_manager import ConversationMemory, MemoryStore
from .assistant import PersonalAssistant

__all__ = [
    "ConversationMemory",
    "MemoryStore",
    "PersonalAssistant",
]
