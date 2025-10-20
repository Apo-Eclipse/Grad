"""
Personal Assistant Agent Implementation

Handles user interactions, context understanding, and personalized responses.
Graph orchestration is handled in main_graph.py - this class focuses on
conversation memory and LLM interaction only.
"""

from typing import Dict, Any, Optional
from langchain_core.prompts import ChatPromptTemplate
from LLMs.azure_models import azure_llm
from .memory_manager import ConversationMemory, MemoryStore, UserProfile
from datetime import datetime


class PersonalAssistant:
    """
    Personal Assistant Agent that maintains conversation memory and provides personalized responses.
    Does NOT handle agent routing - that's managed by main_graph.py
    """

    def __init__(self, user_id: str, user_name: str = "User"):
        """
        Initialize the Personal Assistant.

        Args:
            user_id: Unique identifier for the user
            user_name: Human-readable name of the user
        """
        self.user_id = user_id
        self.user_name = user_name

        # Initialize memory storage
        self.memory_store = MemoryStore()
        self.conversation_memory = ConversationMemory(
            user_id=user_id,
            max_turns=20,
            memory_store=self.memory_store
        )

        # Initialize or load user profile
        profile = self.memory_store.get_user_profile(user_id)
        if not profile:
            profile = UserProfile(
                user_id=user_id,
                name=user_name,
                preferences={}
            )
            self.memory_store.save_user_profile(profile)
        self.user_profile = profile

        # System prompt for the assistant
        self.system_prompt = """You are a helpful and empathetic Personal Assistant. Your role is to:

1. **Engage Conversationally**: Have natural, friendly conversations with the user.
2. **Remember Context**: Reference previous conversations and preferences to provide personalized responses.
3. **Assist Proactively**: Anticipate user needs based on their patterns and preferences.
4. **Be Respectful**: Maintain professional boundaries while being warm and approachable.
5. **Provide Actionable Help**: Offer specific, practical advice when requested.

Guidelines:
- Keep responses concise but informative (2-3 paragraphs max unless asked otherwise).
- If you don't know something, admit it and offer to help find information.
- Use the user's name ({user_name}) occasionally to create a personal touch.
- Remember and respect the user's stated preferences and constraints.
- If the user provides new information about preferences, acknowledge that you'll remember it.
"""

    def invoke(self, user_message: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process a user message and generate a response.

        Args:
            user_message: The user's input message
            context: Optional additional context (may include agent_result, routing_decision)

        Returns:
            Dictionary with response and metadata
        """
        history_summary = self.conversation_memory.get_context_summary()
        
        # Check if we have analysis/data context to reflect on
        agent_result = context.get("agent_result", "") if context else ""
        routing_decision = context.get("routing_decision", "") if context else ""
        
        # Build context-aware prompts
        if routing_decision == "behaviour_analyst" and agent_result:
            # Add analysis reflection to system prompt
            analysis_summary = str(agent_result)[:300] if agent_result else "Analysis completed"
            system_prompt = f"""You are a helpful and empathetic Personal Assistant. Your role is to:

1. **Engage Conversationally**: Have natural, friendly conversations with the user.
2. **Remember Context**: Reference previous conversations and preferences to provide personalized responses.
3. **Assist Proactively**: Anticipate user needs based on their patterns and preferences.
4. **Be Respectful**: Maintain professional boundaries while being warm and approachable.
5. **Provide Actionable Help**: Offer specific, practical advice when requested.

CURRENT ANALYSIS CONTEXT:
The user just received financial analysis. Reflect deeply on the insights provided and offer thoughtful commentary about what it means for their financial behavior and patterns. Help them understand the implications of the analysis.

Use the user's name ({self.user_name}) occasionally to create a personal touch."""
            
            human_prompt = f"Analysis result: {analysis_summary}\n\nUser said: {{user_message}}\n\nPlease provide thoughtful reflection on this analysis and what it means for them."
            
            prompt_template = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("human", human_prompt)
            ])
            
            formatted_prompt = prompt_template.format_prompt(user_message=user_message)
        else:
            # Standard conversation prompt
            system_prompt = self.system_prompt
            human_prompt = "{context_summary}\n\nUser Preferences: {preferences}\n\nCurrent message: {user_message}"
            
            prompt_template = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("human", human_prompt)
            ])
            
            formatted_prompt = prompt_template.format_prompt(
                user_name=self.user_name,
                context_summary=history_summary,
                preferences=str(self.user_profile.preferences) if self.user_profile.preferences else "No preferences recorded.",
                user_message=user_message
            )

        # Get response from LLM
        llm_response = azure_llm.invoke(formatted_prompt)
        assistant_response = llm_response.content

        # Add to memory
        self.conversation_memory.add_turn(
            user_message=user_message,
            assistant_response=assistant_response,
            context=context or {},
            metadata={
                "model": "azure_llm",
                "timestamp": datetime.now().isoformat()
            }
        )

        # Update user profile
        self.user_profile.conversation_count += 1
        self.user_profile.last_interaction = datetime.now().isoformat()
        self.memory_store.update_user_profile(
            self.user_id,
            conversation_count=self.user_profile.conversation_count,
            last_interaction=self.user_profile.last_interaction
        )

        return {
            "response": assistant_response,
            "user_id": self.user_id,
            "timestamp": datetime.now().isoformat(),
            "memory_updated": True
        }

    def ainvoke(self, user_message: str, context: Optional[Dict[str, Any]] = None):
        """
        Async version of invoke. Currently wraps the sync method.
        Can be enhanced with async LLM calls in the future.
        """
        return self.invoke(user_message, context)

    def get_memory_summary(self) -> Dict[str, Any]:
        """Get a summary of the conversation memory and user profile."""
        stats = self.conversation_memory.get_statistics()
        return {
            "user_id": self.user_id,
            "user_name": self.user_name,
            "conversation_stats": stats,
            "user_preferences": self.user_profile.preferences,
            "total_conversations": self.user_profile.conversation_count,
            "last_interaction": self.user_profile.last_interaction
        }

    def set_preference(self, key: str, value: Any) -> bool:
        """
        Set or update a user preference.

        Args:
            key: The preference key
            value: The preference value

        Returns:
            True if successful, False otherwise
        """
        self.user_profile.preferences[key] = value
        return self.memory_store.update_user_profile(
            self.user_id,
            preferences=self.user_profile.preferences
        )

    def get_preference(self, key: str, default: Any = None) -> Any:
        """
        Retrieve a user preference.

        Args:
            key: The preference key
            default: Default value if not found

        Returns:
            The preference value or default
        """
        return self.user_profile.preferences.get(key, default)

    def clear_memory(self):
        """Clear the conversation history."""
        self.conversation_memory.clear_history()

    def get_conversation_history(self, limit: int = 10) -> str:
        """
        Get formatted conversation history.

        Args:
            limit: Maximum number of turns to retrieve

        Returns:
            Formatted conversation history string
        """
        return self.conversation_memory.get_full_history()
