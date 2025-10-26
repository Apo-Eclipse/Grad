# Personal Assistant REST API Guide

This document explains how the REST API inside the `api/` folder works. It walks through the project layout, describes the purpose of each file, and traces a typical request so a newcomer can follow what happens on the server.

---

## Directory Overview

```
api/
├── api_config/              # Django project settings and URL wiring
├── personal_assistant_api/   # Application with all endpoints and services
├── data/                    # Optional SQLite cache (not used in production)
├── manage.py                # Django command-line utility
├── requirements.txt         # Python dependencies for the API
└── run_server.py            # Waitress production server entry point
```

The API is built with Django plus django-ninja. Django handles the web server plumbing; django-ninja provides fast, type-safe REST routing.

---

## File-by-File Explanation

### Top-Level Helpers

| File | Role |
| ---- | ---- |
| `manage.py` | Runs common Django commands (`runserver`, `migrate`, etc.). |
| `run_server.py` | Starts the API with the Waitress WSGI server for production deployments or Windows services. |
| `requirements.txt` | Lists the packages needed to run this API (`Django`, `django-ninja`, `psycopg2-binary`, etc.). |

### `api_config/` (Django Project)

| File | Role |
| ---- | ---- |
| `__init__.py` | Marks the directory as a Python package. |
| `settings.py` | Central configuration: loads `.env`, configures PostgreSQL, allowed hosts, CORS, and installed apps (`personal_assistant_api`). |
| `urls.py` | Registers the django-ninja API instance so all routes live under `/api/`. |
| `asgi.py` | ASGI entry point (kept for completeness). |
| `wsgi.py` | WSGI entry point used by Waitress and `runserver`. |

### `personal_assistant_api/` (Application Code)

| File | Role |
| ---- | ---- |
| `__init__.py` | Package marker. |
| `admin.py` | Empty stub (Django admin is not used here). |
| `apps.py` | App configuration class (`PersonalAssistantApiConfig`). |
| `schemas.py` | Pydantic models defining request/response payloads (e.g., `AnalysisRequestSchema`, `ConversationResponseSchema`). |
| `services.py` | Service layer that bootstraps the LangGraph orchestrator and exposes `PersonalAssistantService.run_analysis`. |
| `api.py` | Main REST endpoints for starting conversations and analyzing user input. Handles persistence to `chat_messages` and `chat_conversations`. |
| `db_retrieval.py` | Additional REST endpoints for reading domain data (transactions, budgets, goals, analytics) and executing guarded SQL queries. |

### `data/`
- Contains `personal_assistant_memory.db`, a local SQLite database used when Postgres is not available. Production runs should instead supply Postgres credentials via environment variables.

---

## Request Trace (Step by Step)

This section traces what happens when the CLI runs:

```text
POST /api/personal_assistant/analyze
{
  "query": "show my October transactions",
  "conversation_id": 61,
  "user_id": 3
}
```

1. **Router receives the request**  
   - File: `personal_assistant_api/api.py`  
   - Function: `analyze` (decorated with `@router.post("analyze", ...)`)  
   - Validates input with `AnalysisRequestSchema`, logs debug info.

2. **Service layer prepares orchestration**  
   - File: `personal_assistant_api/services.py`  
   - Function: `PersonalAssistantService.run_analysis`  
   - If the LangGraph orchestrator is not yet loaded, it imports `graphs.main_graph.main_orchestrator_graph`.  
   - Builds the orchestrator input state: `user_id`, `conversation_id`, `user_message`, and optional metadata.

3. **LangGraph orchestrator runs**  
   - File: `graphs/main_graph.py` (outside the API folder but loaded here)  
   - Key nodes:  
     - `personal_assistant_orchestrator`: decides routing using the LLM.  
     - `database_agent` / `behaviour_analyst`: perform SQL retrieval or deeper analysis.  
     - `personal_assistant_response`: produces the final conversational answer.  
   - Returns a dictionary with `final_output`, `data`, `has_data`, `agents_used`, etc.

4. **Service layer returns results**  
   - File: `personal_assistant_api/services.py`  
   - The result from the orchestrator is passed back to `api.py`.

5. **Messages are stored in the database**  
   - File: `personal_assistant_api/api.py`  
   - Helper: `_store_messages_sync`  
   - Inserts the user query and assistant response (and any JSON data payload) into `chat_messages`, updating `chat_conversations.last_message_at`.

6. **Response sent to client**  
   - The `analyze` endpoint returns `{"final_output": "...", "data": [...], "conversation_id": 61}`.  
   - The CLI prints the assistant text and renders the table if `data` is present.

Additional endpoints follow the same pattern: Ninja router -> optional service function -> database access -> JSON response.

---

## Conversation Start Trace

When `main.py` starts a conversation, it calls:

```text
POST /api/personal_assistant/conversations/start
{
  "user_id": 3,
  "channel": "web"
}
```

Flow:
1. `personal_assistant_api/api.py:start_conversation` inserts a row into `chat_conversations` (SQL executed via Django cursor).
2. Returns `{ "conversation_id": <new id>, "user_id": 3, "channel": "web", "started_at": ... }`.
3. CLI stores `conversation_id` and uses it for subsequent analyze calls.

---

## Additional Data Endpoints

- `GET /api/database/transactions?user_id=3`  
  Returns recent transactions by delegating to `personal_assistant_api/db_retrieval.py:get_transactions`.

- `GET /api/database/messages?conversation_id=61`  
  Fetches stored chat history. Used by the Personal Assistant agent to rebuild conversation context.

- `POST /api/database/execute/select`  
  Executes a SELECT query issued by the database agent. Guarded to only allow `SELECT`/`WITH` statements and automatically adds a `LIMIT` if missing.

These routes reuse Django’s DB cursor (`connection.cursor()`) with parameterized queries to avoid SQL injection.

---

## Environment and Setup

1. Create a `.env` file at the project root (the same `.env` is used by both the API and the orchestrator):
   ```
   DJANGO_SECRET_KEY=replace_me
   DB_HOST=hostname
   DB_USER=username
   DB_PASSWORD=password
   DB_NAME=database
   ```
2. Install dependencies: `pip install -r requirements.txt`.
3. Run development server: `python manage.py runserver 0.0.0.0:8000`.
4. View interactive API docs: `http://localhost:8000/api/docs`.
5. Production: `python run_server.py` (starts Waitress).

---

## Tips for Beginners

- **Routers**: Functions decorated with `@router.get` or `@router.post` become HTTP endpoints. Their first argument is always `request`; query parameters and bodies are validated against Pydantic schemas.
- **Services**: `services.py` keeps orchestration logic separate from HTTP handling. This makes it easier to test and reuse.
- **Schemas**: Describe the structure of input and output data. They also drive automatic documentation in `/api/docs`.
- **Database access**: For data endpoints, we use raw SQL through Django’s connection. Always parameterize inputs to stay safe.
- **Error handling**: The service layer catches initialization errors, and `_store_messages_sync` wraps inserts in a try/except with logging so a write failure does not crash the API call.

---

By following the request trace and the file descriptions above, a new developer can navigate the API, understand how requests are processed, and know where to plug in new routes or modify existing behaviors. Add team-specific notes (Postgres setup, common queries, etc.) here as needed.
