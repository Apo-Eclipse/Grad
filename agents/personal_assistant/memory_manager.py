"""
Memory Management Module for Personal Assistant

Handles conversation history and user profiles via REST API endpoints.
Stores conversation context in memory for the current session.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field
import httpx

@dataclass
class ConversationTurn:
    """Represents a single conversation message."""
    timestamp: str
    message: str
    sender: str  # "user" or "assistant" (or other agent names)


@dataclass
class UserProfile:
    """Stores persistent user information and preferences."""
    user_id: str
    name: str
    preferences: Dict[str, Any] = field(default_factory=dict)
    conversation_count: int = 0
    last_interaction: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class ConversationMemory:
    """
    In-memory conversation buffer with API persistence.
    Maintains recent conversation context for the current session.
    Uses REST API endpoints for storing messages in PostgreSQL.
    """

    API_BASE_URL = "http://localhost:8000/api"

    def __init__(
        self,
        user_id: str,
        conversation_id: Optional[str] = None
    ):
        """
        Initialize conversation memory.

        Args:
            user_id: Unique identifier for the user
            conversation_id: Optional existing conversation ID
        """
        self.user_id = user_id
        self.conversation_id = conversation_id
        self.conversation_history: List[ConversationTurn] = []

    def retrieve_conversation(self, conversation_id: str) -> bool:
        """
        Retrieve an existing conversation via API endpoint.
        
        Args:
            conversation_id: The ID of the conversation to retrieve
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert to string and handle empty/None
            conversation_id = str(conversation_id) if conversation_id else ""
            
            # Handle empty conversation_id
            if not conversation_id or conversation_id.strip() == "":
                self.conversation_history = []
                return True  # Not an error, just no history yet
            
            self.conversation_id = conversation_id
            
            # Clear existing history
            self.conversation_history = []
            
            # Fetch all messages for this conversation from the API
            with httpx.Client() as client:
                response = client.get(
                    f"{self.API_BASE_URL}/database/messages",
                    params={
                        "conversation_id": int(conversation_id),
                        "limit": 1000
                    },
                    timeout=10.0
                )
                
                if response.status_code != 200:
                    return False
                
                # API returns a list directly, not wrapped in {"data": [...]}
                response_data = response.json()
                messages = response_data if isinstance(response_data, list) else response_data.get("data", [])
                
                # Messages come back in DESC order (newest first), so reverse to get chronological order
                messages = list(reversed(messages))
                
                # Store each message as a turn with sender information
                for msg in messages:
                    sender = msg.get("source_agent", "unknown")
                    content_type = msg.get("content_type", "text")
                    content = msg.get("content", "")
                    
                    # Skip pure JSON data messages (they are just data, not meaningful text)
                    if content_type == "json":
                        continue
                    
                    turn = ConversationTurn(
                        timestamp=msg.get("created_at", datetime.now().isoformat()),
                        message=content,
                        sender=sender
                    )
                    self.conversation_history.append(turn)
                
                return True
        except Exception as e:
            print(f"[DEBUG] Error retrieving conversation: {str(e)}")
            return False

    def get_context_summary(self) -> str:
        """Generate a summary of recent conversation context."""
        if not self.conversation_history:
            return "No previous conversation history available. This is the start of a new conversation."
        summary = "Recent conversation context (last 5 messages):\n"
        for i, turn in enumerate(self.conversation_history[-5:], 1):
            summary += f"\n{i}. [{turn.sender}] {turn.message}\n"
        return summary

    def get_full_history(self) -> str:
        """Get the full conversation history as a formatted string."""
        if not self.conversation_history:
            return "No conversation history."

        history = ""
        for turn in self.conversation_history:
            history += f"[{turn.sender}] {turn.message}\n\n"

        return history


    def get_statistics(self) -> Dict[str, Any]:
        """Get conversation statistics."""
        return {
            "total_messages": len(self.conversation_history),
            "first_message": self.conversation_history[0].timestamp if self.conversation_history else None,
            "last_message": self.conversation_history[-1].timestamp if self.conversation_history else None,
            "total_tokens": sum(len(turn.message.split()) for turn in self.conversation_history)
        }        