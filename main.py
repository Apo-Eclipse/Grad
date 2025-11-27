from __future__ import annotations

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

    success, data = request_json("POST", "/database/execute/modify", json_body=payload)
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


def conversation_loop(user_id: int, user_name: str) -> None:
    conversation = start_conversation(user_id=user_id, channel="web")
    if not conversation:
        print("Failed to start conversation. Make sure the API is reachable.")
        return

    conversation_id = conversation.get("conversation_id")
    print(f"Conversation started (ID: {conversation_id})\n")

    while True:
        user_input = input(f"\n{user_name}: ").strip()
        if user_input.lower() in {"exit", "quit", "bye"}:
            print(f"\nGoodbye {user_name}!")
            break
        if not user_input:
            continue

        result = analyze_query(user_input, conversation_id, user_id)
        if not result:
            continue

        final_output = result.get("final_output", "")
        print(f"\nAssistant: {final_output}")
        display_data(result)
        print(f"\n[Conversation ID: {conversation_id}]")


def main() -> None:
    global API_BASE_URL
    API_BASE_URL = detect_api_base_url()
    source_note = "detected locally" if API_BASE_URL.startswith("http://127.0.0.1") or API_BASE_URL.startswith("http://localhost") else "using configured/remote endpoint"

    print("\n" + "=" * 80)
    print("Personal Assistant CLI")
    print("=" * 80)
    print(f"Connecting to API at: {API_BASE_URL} ({source_note})")

    user_id, profile = choose_user()
    if not user_id:
        print("Unable to determine a valid user ID. Exiting.")
        return

    user_name = (
        f"{profile.get('first_name', '')} {profile.get('last_name', '')}".strip()
        if profile
        else f"User {user_id}"
    ) or f"User {user_id}"

    print(f"\nWelcome {user_name}! (type 'exit' to quit)\n")
    conversation_loop(user_id, user_name)


if __name__ == "__main__":
    main()
