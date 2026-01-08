from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import json
import os
from datetime import datetime
from typing import Dict, Optional, Tuple

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

# Local API only - no remote fallback
API_BASE_URL = "http://127.0.0.1:8000/api"  

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
    try:
        response = requests.request(
            method,
            url,
            params=params,
            json=json_body,
            timeout=timeout,
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

    try:
        detail = response.json()
    except ValueError:
        detail = response.text
    print(f"Error calling {path}: {detail}")
    return False, None


def detect_api_base_url() -> str:
    """Try local endpoints only (8000 and 8080)."""
    candidates = ["http://127.0.0.1:8000/api", "http://localhost:8000/api", "http://127.0.0.1:8080/api", "http://localhost:8080/api"]

    for base in candidates:
        health_url = f"{base}/personal_assistant/health"
        try:
            resp = requests.get(health_url, timeout=10)
            if resp.status_code == 200:
                return base
        except requests.RequestException:
            continue
    
    # Default to local port 8000
    return "http://127.0.0.1:8000/api"


def start_conversation(user_id: int, channel: str = "web") -> Optional[Dict]:
    success, data = request_json(
        "POST",
        "/personal_assistant/conversations/start",
        json_body={"user_id": user_id, "channel": channel},
    )
    return data if success else None


def analyze_query(query: str, conversation_id: Optional[int], user_id: Optional[int]) -> Optional[Dict]:
    payload = {"query": query}
    if conversation_id:
        payload["conversation_id"] = conversation_id
    if user_id:
        payload["user_id"] = user_id

    success, data = request_json("POST", "/personal_assistant/analyze", json_body=payload)
    return data if success else None


def get_user(user_id: int) -> Optional[Dict]:
    success, data = request_json("GET", f"/database/users/{user_id}")
    return data if success else None


def prompt_required(prompt: str) -> str:
    value = input(prompt).strip()
    while not value:
        print("This field is required.")
        value = input(prompt).strip()
    return value


def prompt_enum(label: str, options: Dict[str, str]) -> Optional[str]:
    print(f"\n{label}:")
    for key, value in options.items():
        print(f"  {key}. {value}")
    selection = input("Choose an option (leave blank to skip): ").strip()
    if not selection:
        return None
    if selection not in options:
        print("Invalid choice. Leaving empty.")
        return None
    return options[selection]


def prompt_date(prompt: str) -> str:
    while True:
        value = input(prompt).strip()
        try:
            return datetime.strptime(value, "%Y-%m-%d").strftime("%Y-%m-%d")
        except ValueError:
            print("Invalid format. Please use YYYY-MM-DD.")


def upsert_user_via_api() -> Optional[int]:
    """Collect user information and send it to the modify endpoint."""
    print("\nLet's capture some personal details.")
    user_id_raw = input("Enter a numeric user ID to use (e.g., 1001): ").strip()
    if not user_id_raw.isdigit():
        print("User ID must be numeric. Aborting user creation.")
        return None
    user_id = int(user_id_raw)

    first_name = input("First name: ").strip() or "User"
    last_name = input("Last name: ").strip() or "Guest"
    job_title = prompt_required("Job title (required): ").strip()
    address = prompt_required("Address (required): ").strip()
    employment_status = prompt_enum("Employment status options", EMPLOYMENT_OPTIONS)
    education_level = prompt_enum("Education level options", EDUCATION_OPTIONS)
    birthday = prompt_date("Birthday (YYYY-MM-DD, required): ")
    gender = prompt_enum("Gender options", GENDER_OPTIONS)

    sql = """
        INSERT INTO users (
            user_id, first_name, last_name, job_title, address,
            employment_status, education_level, birthday, gender, created_at, updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
        ON CONFLICT (user_id) DO UPDATE SET
            first_name = EXCLUDED.first_name,
            last_name = EXCLUDED.last_name,
            job_title = EXCLUDED.job_title,
            address = EXCLUDED.address,
            employment_status = EXCLUDED.employment_status,
            education_level = EXCLUDED.education_level,
            birthday = EXCLUDED.birthday,
            gender = EXCLUDED.gender,
            updated_at = NOW();
    """

    payload = {
        "query": sql,
        "params": [
            user_id,
            first_name,
            last_name,
            job_title,
            address,
            employment_status,
            education_level,
            birthday,
            gender,
        ],
    }

    success, data = request_json("POST", "/database/analytics/execute/modify", json_body=payload)
    if success and data and data.get("success"):
        print(f"User {user_id} saved successfully.")
        return user_id
    print(f"Failed to save user: {data}")
    return None


def choose_user() -> Tuple[int, Optional[Dict]]:
    choice = input(
        "\nDo you want to (1) use an existing user or (2) create/update a user? [1/2]: "
    ).strip() or "1"

    if choice == "2":
        user_id = upsert_user_via_api()
        if user_id:
            return user_id, get_user(user_id)
        return 0, None

    user_id_raw = input("Enter existing user ID: ").strip()
    if user_id_raw.isdigit():
        user_id = int(user_id_raw)
        return user_id, get_user(user_id)

    print("Invalid user ID. Falling back to default user 3.")
    return 3, get_user(3)


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

def run_mode_loop(agent_key: str, user_id: int, user_name: str, conversation_id: int) -> int:
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
        # Start a generic conversation entry in the DB to track this thread
        # Note: All agents share the 'chat_conversations' table, but we track IDs separately in the dict
        # The 'channel' 'web' is generic.
        conversation = start_conversation(user_id=user_id, channel=f"cli-{slug}")
        if not conversation:
            print("Error: Could not start new conversation session.")
            return 0
        conversation_id = conversation.get("conversation_id")
        print(f"Started new session {conversation_id} for {agent_name}.")

    while True:
        user_input = input(f"\n{user_name} ({slug}): ").strip()
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
    # Local API only - no remote fallback
    # API_BASE_URL is already defined at module level as "http://127.0.0.1:8000/api"
    
    print("\n" + "=" * 80)
    print("Personal Assistant CLI - Multi-Agent Mode")
    print("=" * 80)
    print(f"Connecting to API at: {API_BASE_URL} (Local Only)")

    user_id, profile = choose_user()
    if not user_id:
        print("Unable to determine a valid user ID. Exiting.")
        return

    user_name = (
        f"{profile.get('first_name', '')} {profile.get('last_name', '')}".strip()
        if profile
        else f"User {user_id}"
    ) or f"User {user_id}"

    # Dictionary to persist conversation IDs per agent for this session
    # Key: agent_key (str), Value: conversation_id (int)
    agent_conversations: Dict[str, int] = {}

    print(f"\nWelcome {user_name}!")

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
            updated_cid = run_mode_loop(choice, user_id, user_name, current_cid)
            # Update the stored ID so we can resume later
            if updated_cid:
                agent_conversations[choice] = updated_cid
        else:
            print("Invalid choice.")


if __name__ == "__main__":
    main()
