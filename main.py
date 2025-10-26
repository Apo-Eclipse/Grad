from dotenv import load_dotenv
load_dotenv()
import requests
import json
import pandas as pd
import asyncio
import sys

API_BASE_URL = "http://localhost:8000/api"

# def process_queries():
#     queries_to_run = json.load(open('queries_to_run.json', 'r', encoding='utf-8'))
#     conn = sqlite3.connect('./data/database.db')
#     tables = []
#     for query in queries_to_run:
#         table = pd.read_sql_query(queries_to_run[query], conn)
#         tables.append("Query: " + query + "\nTable:\n" + table.to_string(index=False))
#     conn.close()
#     return tables

# def process_tables(tables):
#     explanations = []
#     for table in tables:
#         explanation = Explainer_agent.invoke({"request": table})
#         explanations.append(explanation.explanation)
#     return explanations  
    
def start_conversation(user_id, channel="web"):
    """Start a new conversation via API."""
    try:
        response = requests.post(
            f"{API_BASE_URL}/personal_assistant/conversations/start",
            json={"user_id": user_id, "channel": channel}
        )
        if response.status_code == 200:
            data = response.json()
            return data
        else:
            print(f"Error starting conversation: {response.json()}")
            return None
    except Exception as e:
        print(f"Connection error: {e}")
        return None


def analyze_query(query, conversation_id=None, user_id=None):
    """Send query to API for analysis."""
    try:
        payload = {"query": query}
        if conversation_id:
            payload["conversation_id"] = conversation_id
        if user_id:
            payload["user_id"] = user_id
        response = requests.post(
            f"{API_BASE_URL}/personal_assistant/analyze",
            json=payload
        )
        if response.status_code == 200:
            data = response.json()
            return data
        else:
            print(f"Error analyzing query: {response.json()}")
            return None
    except Exception as e:
        print(f"Connection error: {e}")
        return None


def get_messages(conversation_id):
    """Get all messages from a conversation."""
    try:
        response = requests.get(
            f"{API_BASE_URL}/database/messages",
            params={"conversation_id": conversation_id}
        )
        if response.status_code == 200:
            data = response.json()
            return data
        else:
            print(f"Error fetching messages: {response.json()}")
            return None
    except Exception as e:
        print(f"Connection error: {e}")
        return None


def main():
    """Interactive conversation with PersonalAssistant via REST API."""
    user_id = 3
    user_name = "user"
    
    print("\n" + "="*80)
    print(f"👋 Welcome {user_name}! Chat with PersonalAssistant (type 'exit' to quit)")
    print("="*80 + "\n")
    
    # Start a new conversation
    conversation_data = start_conversation(user_id=user_id, channel="web")
    if not conversation_data:
        print("Failed to start conversation. Make sure API is running at", API_BASE_URL)
        return
    
    conversation_id = conversation_data.get("conversation_id")
    print(f"✅ Conversation started (ID: {conversation_id})\n")
    
    while True:
        user_input = input(f"\n{user_name}: ").strip()
        
        if user_input.lower() in ['exit', 'quit', 'bye']:
            print(f"\n👋 Goodbye {user_name}!")
            break
        
        if not user_input:
            continue
        
        # Send query to API
        result = analyze_query(
            query=user_input,
            conversation_id=conversation_id,
            user_id=user_id
        )
        
        if not result:
            continue
        
        # Display response
        final_output = result.get("final_output", "")
        data = result.get("data")
        
        print(f"\n🤖 Assistant: {final_output}")
        
        # Display data if available
        if data:
            if isinstance(data, list) and len(data) > 0:
                df = pd.DataFrame(data)
                print(f"\n{df.to_string(index=False)}")
            elif isinstance(data, dict):
                print(f"\nData: {json.dumps(data, indent=2)}")
        
        print(f"\n[Conversation ID: {conversation_id}]")

if __name__ == "__main__":
    main()