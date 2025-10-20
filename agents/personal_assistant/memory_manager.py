"""
Memory Management Module for Personal Assistant

Handles conversation history, user preferences, and interaction records.
Implements both in-memory and persistent storage options.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, date, time
import json
from decimal import Decimal
from dataclasses import dataclass, asdict, field
import sqlite3
import os


class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle Decimal, date, datetime, and time objects."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, (date, datetime, time)):
            return obj.isoformat()
        return super().default(obj)


@dataclass
class ConversationTurn:
    """Represents a single conversation turn (user message + assistant response)."""
    timestamp: str
    user_message: str
    assistant_response: str
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UserProfile:
    """Stores persistent user information and preferences."""
    user_id: str
    name: str
    preferences: Dict[str, Any] = field(default_factory=dict)
    conversation_count: int = 0
    last_interaction: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class MemoryStore:
    """
    Persistent memory storage using SQLite.
    Stores conversation history and user profiles.
    """

    def __init__(self, db_path: str = "data/personal_assistant_memory.db"):
        """Initialize the memory store with SQLite database."""
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._initialize_db()

    def _initialize_db(self):
        """Create database tables if they don't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create conversations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                user_message TEXT NOT NULL,
                assistant_response TEXT NOT NULL,
                context TEXT,
                metadata TEXT
            )
        """)

        # Create user profiles table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                preferences TEXT,
                conversation_count INTEGER DEFAULT 0,
                last_interaction TEXT,
                created_at TEXT NOT NULL
            )
        """)

        # Create indices for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_id 
            ON conversations(user_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp 
            ON conversations(timestamp)
        """)

        conn.commit()
        conn.close()

    def save_conversation(
        self, user_id: str, turn: ConversationTurn
    ) -> bool:
        """Save a conversation turn to the database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO conversations 
                (user_id, timestamp, user_message, assistant_response, context, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                turn.timestamp,
                turn.user_message,
                turn.assistant_response,
                json.dumps(turn.context, cls=CustomJSONEncoder),
                json.dumps(turn.metadata, cls=CustomJSONEncoder)
            ))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error saving conversation: {e}")
            return False

    def get_conversation_history(
        self, user_id: str, limit: int = 10
    ) -> List[ConversationTurn]:
        """Retrieve conversation history for a user."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT timestamp, user_message, assistant_response, context, metadata
                FROM conversations
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (user_id, limit))

            results = cursor.fetchall()
            conn.close()

            turns = []
            for row in reversed(results):  # Reverse to maintain chronological order
                turns.append(ConversationTurn(
                    timestamp=row[0],
                    user_message=row[1],
                    assistant_response=row[2],
                    context=json.loads(row[3]) if row[3] else {},
                    metadata=json.loads(row[4]) if row[4] else {}
                ))
            return turns
        except Exception as e:
            print(f"Error retrieving conversation history: {e}")
            return []

    def save_user_profile(self, profile: UserProfile) -> bool:
        """Save or update a user profile."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO user_profiles
                (user_id, name, preferences, conversation_count, last_interaction, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                profile.user_id,
                profile.name,
                json.dumps(profile.preferences),
                profile.conversation_count,
                profile.last_interaction,
                profile.created_at
            ))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error saving user profile: {e}")
            return False

    def get_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """Retrieve a user profile."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT user_id, name, preferences, conversation_count, last_interaction, created_at
                FROM user_profiles
                WHERE user_id = ?
            """, (user_id,))

            result = cursor.fetchone()
            conn.close()

            if result:
                return UserProfile(
                    user_id=result[0],
                    name=result[1],
                    preferences=json.loads(result[2]) if result[2] else {},
                    conversation_count=result[3],
                    last_interaction=result[4],
                    created_at=result[5]
                )
            return None
        except Exception as e:
            print(f"Error retrieving user profile: {e}")
            return None

    def update_user_profile(self, user_id: str, **kwargs) -> bool:
        """Update specific fields of a user profile."""
        try:
            profile = self.get_user_profile(user_id)
            if not profile:
                return False

            for key, value in kwargs.items():
                if hasattr(profile, key):
                    setattr(profile, key, value)

            return self.save_user_profile(profile)
        except Exception as e:
            print(f"Error updating user profile: {e}")
            return False


class ConversationMemory:
    """
    In-memory conversation buffer with optional persistent storage.
    Maintains recent conversation context for the current session.
    """

    def __init__(
        self,
        user_id: str,
        max_turns: int = 20,
        memory_store: Optional[MemoryStore] = None
    ):
        """
        Initialize conversation memory.

        Args:
            user_id: Unique identifier for the user
            max_turns: Maximum number of turns to keep in memory
            memory_store: Optional persistent storage backend
        """
        self.user_id = user_id
        self.max_turns = max_turns
        self.memory_store = memory_store
        self.conversation_history: List[ConversationTurn] = []
        self.user_profile: Optional[UserProfile] = None

        # Load from persistent storage if available
        if self.memory_store:
            self._load_from_storage()

    def _load_from_storage(self):
        """Load conversation history and user profile from persistent storage."""
        if not self.memory_store:
            return

        # Load user profile
        self.user_profile = self.memory_store.get_user_profile(self.user_id)

        # Load recent conversation history
        self.conversation_history = self.memory_store.get_conversation_history(
            self.user_id, limit=self.max_turns
        )

    def add_turn(
        self,
        user_message: str,
        assistant_response: str,
        context: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ConversationTurn:
        """
        Add a conversation turn to memory.

        Args:
            user_message: The user's input
            assistant_response: The assistant's response
            context: Optional context data
            metadata: Optional metadata

        Returns:
            The added ConversationTurn
        """
        turn = ConversationTurn(
            timestamp=datetime.now().isoformat(),
            user_message=user_message,
            assistant_response=assistant_response,
            context=context or {},
            metadata=metadata or {}
        )

        self.conversation_history.append(turn)

        # Keep memory buffer within size limit
        if len(self.conversation_history) > self.max_turns:
            self.conversation_history.pop(0)

        # Save to persistent storage
        if self.memory_store:
            self.memory_store.save_conversation(self.user_id, turn)

        return turn

    def get_context_summary(self) -> str:
        """Generate a summary of recent conversation context."""
        if not self.conversation_history:
            return "No previous conversations."

        summary = "Recent conversation context:\n"
        for i, turn in enumerate(self.conversation_history[-5:], 1):  # Last 5 turns
            summary += f"\n{i}. User: {turn.user_message[:100]}...\n"
            summary += f"   Assistant: {turn.assistant_response[:100]}...\n"

        return summary

    def get_full_history(self) -> str:
        """Get the full conversation history as a formatted string."""
        if not self.conversation_history:
            return "No conversation history."

        history = ""
        for turn in self.conversation_history:
            history += f"User: {turn.user_message}\n"
            history += f"Assistant: {turn.assistant_response}\n\n"

        return history

    def clear_history(self):
        """Clear the in-memory conversation history."""
        self.conversation_history.clear()

    def get_statistics(self) -> Dict[str, Any]:
        """Get conversation statistics."""
        return {
            "total_turns": len(self.conversation_history),
            "first_turn": self.conversation_history[0].timestamp if self.conversation_history else None,
            "last_turn": self.conversation_history[-1].timestamp if self.conversation_history else None,
            "total_user_tokens": sum(len(turn.user_message.split()) for turn in self.conversation_history),
            "total_assistant_tokens": sum(len(turn.assistant_response.split()) for turn in self.conversation_history)
        }
