from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import json
import os
import getpass
from datetime import datetime
from typing import Dict, Optional, Tuple

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

# Local API only - no remote fallback
API_BASE_URL = "http://127.0.0.1:8000/api"

# Global Session Token
ACCESS_TOKEN: Optional[str] = None
CURRENT_USER_ID: Optional[int] = None

# Enums
EMPLOYMENT_OPTIONS: Dict[str, str] = {
    "1": "Employed Full-time",
    "2": "Employed Part-time",
    "3": "Unemployed",
    "4": "Retired",
}

EDUCATION_OPTIONS: Dict[str, str] = {
    "1": "High school",
    "2": "Associate degree",
    "3": "Bachelor degree",
    "4": "Masters Degree",
    "5": "PhD",
}

GENDER_OPTIONS: Dict[str, str] = {
    "1": "male",
    "2": "female",
}


def request_json(
    method: str,
    path: str,
    *,
    params: Optional[Dict] = None,
    json_body: Optional[Dict] = None,
    timeout: int = 300,
) -> Tuple[bool, Optional[Dict]]:
    """Send an HTTP request and return (success, json_payload)."""
    url = f"{API_BASE_URL}{path}"
    headers = {}
    
    # Inject Authorization Header if logged in
    if ACCESS_TOKEN:
        headers["Authorization"] = f"Bearer {ACCESS_TOKEN}"

    try:
        response = requests.request(
            method,
            url,
            params=params,
            json=json_body,
            timeout=timeout,
            headers=headers
        )
    except requests.RequestException as exc:
        print(f"Connection error calling {url}: {exc}")
        return False, None

    if 200 <= response.status_code < 300:
        if response.content:
            try:
                return True, response.json()
            except ValueError:
                return True, None
        return True, None

    # Error Handling
    try:
        detail = response.json()
    except ValueError:
        detail = response.text
    
    # Handle Token Expiration
    if response.status_code == 401:
        print(f"\n[!] Session expired or unauthorized: {detail}")
        # Could auto-logout here, but keeping it simple for now
    
    print(f"Error calling {path}: {detail}")
    return False, None


def login() -> bool:
    """Authenticate user and store token."""
    global ACCESS_TOKEN, CURRENT_USER_ID
    
    print("\n=== LOGIN ===")
    email = input("Email: ").strip()
    password = getpass.getpass("Password: ").strip()

    if not email or not password:
        print("Credentials required.")
        return False

    success, data = request_json("POST", "/auth/login", json_body={"email": email, "password": password})
    
    if success and data and "access" in data:
        ACCESS_TOKEN = data["access"]
        # Fetch user details to get ID
        user_success, user_data = request_json("GET", "/database/user/")
        if user_success and user_data:
             CURRENT_USER_ID = user_data.get("user_id")
             print(f"Login successful! Welcome, {user_data.get('first_name')}.")
             return True
        else:
             print("Login successful but failed to fetch profile.")
             return False
    else:
        print("Login failed. Check credentials.")
        return False


def register() -> bool:
    """Register a new user."""
    print("\n=== REGISTER NEW USER ===")
    username = input("Username: ").strip()
    email = input("Email: ").strip()
    password = getpass.getpass("Password: ").strip()
    first_name = input("First Name: ").strip()
    last_name = input("Last Name: ").strip()
    
    if not all([username, email, password, first_name, last_name]):
         print("All fields are required for basics.")
         return False

    # Optional Details
    print("\n--- Optional Profile Details (Press Enter to skip) ---")
    job_title = input("Job Title: ").strip() or "N/A"
    address = input("Address: ").strip() or "N/A"
    birthday = input("Birthday (YYYY-MM-DD): ").strip()
    if not birthday: birthday = "2000-01-01"
    
    payload = {
        "username": username,
        "email": email,
        "password": password,
        "first_name": first_name,
        "last_name": last_name,
        "job_title": job_title,
        "address": address,
        "birthday": birthday,
        "gender": "male", # default to simplify
        "employment_status": "Employed Full-time",
        "education_level": "Bachelor degree"
    }

    success, data = request_json("POST", "/database/user/", json_body=payload)
    if success:
        print("Registration successful! You can now log in.")
        return True
    else:
        print("Registration failed.")
        return False


def start_conversation(user_id: int, channel: str = "web") -> Optional[Dict]:
    success, data = request_json(
        "POST",
        "/database/conversation/start",
        json_body={"user_id": user_id, "channel": channel},
    )
    return data if success else None


def analyze_query(query: str, conversation_id: Optional[int], user_id: Optional[int]) -> Optional[Dict]:
    payload = {"query": query}
    if conversation_id:
        payload["conversation_id"] = conversation_id
    # Backend usually infers user from Token now, but passing ID is safe fallback for orchestrator
    if user_id:
        payload["user_id"] = user_id

    success, data = request_json("POST", "/personal_assistant/analyze", json_body=payload)
    return data if success else None


def display_data(payload: Dict) -> None:
    data = payload.get("data")
    if not data:
        return
    if isinstance(data, list) and data:
        df = pd.DataFrame(data)
        print(f"\n{df.to_string(index=False)}")
    elif isinstance(data, dict):
        print(f"\nData: {json.dumps(data, indent=2)}")


# --- Agent Request Helpers ---

def request_budget_assist(user_request: str, conversation_id: int, user_id: int) -> Optional[Dict]:
    payload = {"user_id": user_id, "user_request": user_request, "conversation_id": conversation_id}
    success, data = request_json("POST", "/personal_assistant/budget/assist", json_body=payload)
    return data if success else None

def request_goal_assist(user_request: str, conversation_id: int, user_id: int) -> Optional[Dict]:
    payload = {"user_id": user_id, "user_request": user_request, "conversation_id": conversation_id}
    success, data = request_json("POST", "/personal_assistant/goals/assist", json_body=payload)
    return data if success else None

def request_transaction_assist(user_request: str, conversation_id: int, user_id: int) -> Optional[Dict]:
    payload = {"user_id": user_id, "user_request": user_request, "conversation_id": conversation_id}
    success, data = request_json("POST", "/personal_assistant/transaction/assist", json_body=payload)
    return data if success else None


# --- Conversation Logic ---

AGENTS = {
    "1": {"name": "General Analyst", "slug": "general"},
    "2": {"name": "Budget Maker", "slug": "budget"},
    "3": {"name": "Goal Maker", "slug": "goals"},
    "4": {"name": "Transaction Maker", "slug": "transaction"},
}

def run_mode_loop(agent_key: str, user_id: int, conversation_id: int) -> int:
    """
    Runs the chat loop for a specific agent mode. 
    Returns the updated conversation_id (in case it was created/changed).
    """
    agent_info = AGENTS[agent_key]
    agent_name = agent_info["name"]
    slug = agent_info["slug"]
    
    print(f"\n--- Entering {agent_name} Mode ---")
    print(f"(Current Conversation ID: {conversation_id if conversation_id else 'New'})")
    print("Type 'exit' to return to the main menu.\n")

    # If no conversation exists for this agent yet, start one now
    if not conversation_id:
        conversation = start_conversation(user_id=user_id, channel=f"cli-{slug}")
        if not conversation:
            print("Error: Could not start new conversation session.")
            return 0
        conversation_id = conversation.get("conversation_id")
        print(f"Started new session {conversation_id} for {agent_name}.")

    while True:
        user_input = input(f"\n({slug}): ").strip()
        if user_input.lower() in {"exit", "quit", "menu"}:
            print(f"Exiting {agent_name} mode.")
            break
        if not user_input:
            continue

        result = None
        
        # Dispatch to correct agent API
        if slug == "general":
            result = analyze_query(user_input, conversation_id, user_id)
        elif slug == "budget":
            print("Thinking...")
            result = request_budget_assist(user_input, conversation_id, user_id)
        elif slug == "goals":
            print("Thinking...")
            result = request_goal_assist(user_input, conversation_id, user_id)
        elif slug == "transaction":
            print("Thinking...")
            result = request_transaction_assist(user_input, conversation_id, user_id)

        if not result:
            continue

        # Display Response
        if slug == "general":
            final_output = result.get("final_output", "")
            print(f"\n{agent_name}: {final_output}")
            display_data(result)
        else:
            # Maker Agents usually return 'message'
            msg = result.get("message", "")
            print(f"\n{agent_name}: {msg}")
            
            # Show specialized fields if present
            if slug == "budget":
                if result.get("action"): print(f"Action: {result['action']}")
                if result.get("budget_name"): print(f"Budget: {result['budget_name']} (Limit: {result.get('total_limit')})")
            elif slug == "goals":
                if result.get("goal_name"): print(f"Goal: {result['goal_name']}")
                if result.get("plan"): print(f"Plan: {result['plan']}")
            elif slug == "transaction":
                if result.get("amount"): print(f"Transaction: {result['amount']} at {result.get('store_name')}")

            if result.get("is_done"):
                print("[Task Completed]")

    return conversation_id


def main() -> None:
    print("\n" + "=" * 80)
    print("Personal Assistant CLI - Multi-Agent Mode (Localhost)")
    print("=" * 80)
    print(f"Connecting to API at: {API_BASE_URL}")

    # Authentication Loop
    while not ACCESS_TOKEN:
        print("\nAuthentication Required:")
        print("1. Login")
        print("2. Register New User")
        print("q. Quit")
        choice = input("Select: ").strip().lower()
        
        if choice == '1':
            if login():
                break
        elif choice == '2':
            if register():
                if login():
                    break
        elif choice == 'q':
            return
        else:
            print("Invalid choice.")

    # Dictionary to persist conversation IDs per agent for this session
    # Key: agent_key (str), Value: conversation_id (int)
    agent_conversations: Dict[str, int] = {}

    while True:
        print("\n" + "-" * 40)
        print("SELECT AGENT MODE:")
        for key, info in AGENTS.items():
            cid = agent_conversations.get(key, 0)
            status = f"(Active ID: {cid})" if cid else "(No active session)"
            print(f"  {key}. {info['name']} {status}")
        print("  q. Quit Application")
        
        choice = input("\nChoose (1-4, q): ").strip().lower()
        
        if choice == 'q':
            print("Goodbye!")
            break
            
        if choice in AGENTS:
            current_cid = agent_conversations.get(choice, 0)
            updated_cid = run_mode_loop(choice, CURRENT_USER_ID, current_cid)
            if updated_cid:
                agent_conversations[choice] = updated_cid
        else:
            print("Invalid choice.")


if __name__ == "__main__":
    main()
