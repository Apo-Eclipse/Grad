"""
Personal Assistant Agent Implementation

Handles user interactions, context understanding, and personalized responses.
Graph orchestration is handled in main_graph.py - this class focuses on
conversation memory and LLM interaction only.
"""

from typing import Dict, Any, Optional
from datetime import datetime
from langchain_core.prompts import ChatPromptTemplate
from LLMs.azure_models import azure_llm
from .memory_manager import UserProfile


class PersonalAssistant:

    def __init__(self, user_id: str, conversation_id: str, user_name: str = "User"):
        """
        Initialize the Personal Assistant.

        Args:
            user_id: Unique identifier for the user
            conversation_id: The ID of the conversation
            user_name: Human-readable name of the user
        """
        self.user_id = user_id
        self.user_name = user_name
        self.conversation_id = conversation_id

        # Initialize user profile
        self.user_profile = UserProfile(
            user_id=user_id,
            name=user_name
        )

        # System prompt for the assistant
        self.system_prompt = """
        You are a helpful and empathetic Personal Assistant. Your role is to:
        
        1. **Engage Conversationally**: Have natural, friendly conversations with the user.
        2. **Remember Context**: Reference previous conversations to provide personalized responses.
        3. **Assist Proactively**: Anticipate user needs based on their patterns.
        4. **Be Respectful**: Maintain professional boundaries while being warm and approachable.
        5. **Provide Actionable Help**: Offer specific, practical advice when requested.

        Guidelines:
        - Keep responses concise but informative (2-3 paragraphs max unless asked otherwise).
        - If you don't know something, admit it and offer to help find information.
        - Use the user's name ({user_name}) occasionally to create a personal touch.
        """

    def invoke(self, user_message: str, conversation_history: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process a user message and generate a response.

        Args:
            user_message: The user's input message
            conversation_history: The conversation history summary string
            context: Optional additional context (may include agent_result, routing_decision)

        Returns:
            Dictionary with response and metadata
        """
        
        # Check if we have analysis/data context to reflect on
        analysis_summary = context.get("analysis", "") if context else ""
        routing_decision = context.get("routing_decision", "") if context else ""
        
        # Build context-aware prompts
        if routing_decision == "behaviour_analyst":
            # Add analysis reflection to system prompt
            analysis_summary = str(analysis_summary) if analysis_summary else "Analysis completed"
            system_prompt = f"""
            You are a helpful and empathetic Personal Assistant. Your role is to:
            1. **Engage Conversationally**: Have natural, friendly conversations with the user.
            2. **Remember Context**: Reference previous conversations and preferences to provide personalized responses.
            3. **Assist Proactively**: Anticipate user needs based on their patterns and preferences.
            4. **Be Respectful**: Maintain professional boundaries while being warm and approachable.
            5. **Provide Actionable Help**: Offer specific, practical advice when requested.
            6. **Reflect on Analysis**: Thoughtfully reflect on the provided analysis results to help the user understand their financial behavior.
            7. **Interact Naturally**: Keep responses concise but informative (2-3 paragraphs max unless asked otherwise).
            8. **Avoid Repetition**: Ensure your responses are fresh and avoid repeating previous statements.
            9. **Use Numbers and Data**: you have to use numbers and data from the analysis to support your reflections.
            10. Do not mention that you are an AI model or you are receiving data from other agents.
            11. Do not respond with things that not requested from you.
            12. Do not give information outside the scope of the analysis provided.

            CURRENT ANALYSIS CONTEXT:
            The user just received financial analysis. Reflect deeply on the insights provided and offer thoughtful commentary about what it means for their financial behavior and patterns. Help them understand the implications of the analysis.

            Use the user's name ({self.user_name}) occasionally to create a personal touch.
            """
            
            human_prompt = f"Analysis result: {analysis_summary}\n\nUser said: {{user_message}}\n\nPlease provide thoughtful reflection on this analysis and what it means for them."
            
            prompt_template = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("human", human_prompt)
            ])
            
            formatted_prompt = prompt_template.format_prompt(user_message=user_message)
        else:
            system_prompt = self.system_prompt
            human_prompt = "{context_summary}\n\nCurrent message: {user_message}"
            
            prompt_template = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("human", human_prompt)
            ])
            
            formatted_prompt = prompt_template.format_prompt(
                user_name=self.user_name,
                context_summary=conversation_history,
                user_message=user_message
            )
            
        llm_response = azure_llm.invoke(formatted_prompt)
        assistant_response = llm_response.content

        # Update user profile in memory
        self.user_profile.conversation_count += 1
        self.user_profile.last_interaction = datetime.now().isoformat()

        return {
            "response": assistant_response,
            "user_id": self.user_id,
            "timestamp": datetime.now().isoformat(),
            "memory_updated": True
        }