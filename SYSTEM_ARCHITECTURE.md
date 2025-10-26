# Multi-Agent System Architecture & Usage Guide

## Overview
- Multi-agent personal finance assistant composed of specialized agents orchestrated with LangGraph.
- Persists conversations and analysis outputs through a Django Ninja REST API backed by PostgreSQL.
- Provides a CLI chat experience (`main.py`) that communicates exclusively through the REST interface.

```
┌───────────────┐    HTTP POST/GET     ┌──────────────────────────┐
│ CLI Chat User │ ───────────────────▶ │ Django Ninja REST API     │
└───────────────┘                     │ • /personal_assistant/... │
                                      │ • /database/...           │
                                      └────────────┬──────────────┘
                                                   │
                                                   ▼
                                        ┌─────────────────────┐
                                        │ LangGraph Orchestr. │
                                        │ (main_graph)        │
                                        └──────┬──────┬───────┘
                                               │      │
                           ┌───────────────────┘      └───────────────────┐
                           ▼                                              ▼
                ┌──────────────────────┐                      ┌───────────────────────┐
                │ Database Agent       │                      │ Behaviour Analyst     │
                │ (LLM → SQL → API)    │                      │ Sub-graph             │
                └─────────┬───────────┘                      └─────────┬────────────┘
                          │                                              │
                          │ SQL via /database/execute/*                  │ Plans, DB fan-out,
                          ▼                                              ▼ explains, validates
                 ┌──────────────────────┐                      ┌───────────────────────┐
                 │ PostgreSQL           │◀─ chat history ───── │ Personal Assistant     │
                 │ • chat_conversations │                      │ Agent + Memory         │
                 │ • chat_messages      │                      └───────────────────────┘
                 └──────────────────────┘
```

## Core Components

### CLI Chat Client (`main.py`)
- Starts conversations (`POST /personal_assistant/conversations/start`) and submits messages (`POST /personal_assistant/analyze`).
- Prints assistant replies and renders tabular data with `pandas`.
- Pulls message history via `GET /database/messages` for debugging purposes only (the server handles memory automatically).

### REST API Service (`api/`)
- Django 4.2 + django-ninja.
- Configuration: `api/api_config/settings.py` reads environment variables (`DB_*`, `DJANGO_SECRET_KEY`) via `.env`.
- Entry points:
  - `api/personal_assistant_api/api.py`: conversation endpoints, message persistence.
  - `api/personal_assistant_api/db_retrieval.py`: data retrieval & analytics endpoints, custom SQL executors.
  - `api/personal_assistant_api/services.py`: wraps the orchestrator graph and exposes `run_analysis`.
- Run modes:
  - Dev: `python manage.py runserver 0.0.0.0:8000`.
  - Production (Windows-friendly): `python run_server.py` (Waitress).

### LangGraph Orchestrator (`graphs/main_graph.py`)
- State machine with nodes:
  - `personal_assistant_orchestrator`: uses `gpt_oss_llm` structured output to choose `database_agent`, `behaviour_analyst`, or direct response.
  - `database_agent`: invokes the SQL agent pipeline and streams results back to the state.
  - `behaviour_analyst`: runs the analysis sub-graph for multi-step insights.
  - `personal_assistant_response`: calls the Personal Assistant agent to craft conversational replies.
- Maintains `agents_used`, `has_data`, and conversation metadata to persist accurate chat history.

### Agents (`agents/`)
#### Personal Assistant (`personal_assistant/assistant.py`)
- Loads conversation memory via REST (`ConversationMemory`).
- Builds prompts incorporating history summaries and optional analysis context.
- Uses `azure_llm` (`AzureChatOpenAI`) with configurable deployment and API version.

#### Conversation Memory (`personal_assistant/memory_manager.py`)
- Fetches up to 1000 messages from `/api/database/messages`.
- Filters out JSON payloads so the LLM only sees human-readable turns.
- Provides summaries (`get_context_summary`) and statistics for debugging.

#### Database Agent (`database_agent.py`)
- Prompted to emit PostgreSQL 18-compliant SQL restricted to the documented schema.
- Returns structured output (`{"query": "...", "edit": bool}`) using LangChain’s structured parser.
- Execution workflow (see `graphs/database_sub_graph.py`):
  1. `DatabaseAgent.invoke` (run in a background thread to avoid blocking async loop).
  2. If `edit=False`, call `/api/database/execute/select`; else `/api/database/execute/modify`.
  3. Package response data for the orchestrator.

#### Behaviour Analyst (`behaviour_analyst_sub_graph.py`)
- Multi-node LangGraph pipeline:
  - `query_planner`: plan database steps.
  - `db_agent`: execute planned queries in parallel via the database sub-graph.
  - `explainer`: generate human-readable explanations.
  - `validation`: vet explanations and trigger correction loops if needed.
  - `analyser`: summarize findings.
- Routes are controlled by the orchestrator’s decisions and validation feedback loops.

### Additional Agent Packages
- Present but not currently wired into the main orchestration:
  - `presentation_super_agent/`, `Recommendation_agent/`, `trend_analysis_agent/`, `transaction_agent/`.
- Useful for extensions (reports, recommendations, OCR ingestion) but not part of the production flow described here.

## Request Lifecycle
1. **CLI** sends user input to `POST /api/personal_assistant/analyze`.
2. **API service** augments metadata (user/conversation) and calls `PersonalAssistantService.run_analysis`.
3. **LangGraph orchestrator** loads conversation memory and LLM routes to the proper agent.
4. **Selected agent** (database or behaviour) executes, possibly calling back into the API for data.
5. **Personal Assistant** generates final reply using history + agent outputs.
6. **API service** persists:
   - User message (`chat_messages`, source: `User`).
   - Agent data or analysis (source: `DatabaseAgent` or `BehaviourAnalyst` for intermediate messages).
   - Final conversational response (source: `PersonalAssistant`).
7. **API** responds to the CLI with `{"final_output": "...", "data": [...]}`.
8. **CLI** prints the response and renders tabular data when present.

## Data Persistence & Schema
- PostgreSQL tables used:
  - `chat_conversations`: conversation metadata (`conversation_id`, `user_id`, `channel`, timestamps).
  - `chat_messages`: every message or payload, tagged with `sender_type`, `source_agent`, `content`, `content_type`.
  - Financial domain tables (`transactions`, `budget`, `users`, `income`, `goals`) drive analytics.
- `ConversationMemory` fetches message history (newest first) and reverses locally for chronological context.
- Data payloads returned from the database agent are inserted as `content_type = "json"` so they’re persisted but not replayed to the LLM.

## LLM Configuration (`LLMs/`)
- Azure OpenAI clients defined in `LLMs/azure_models.py`:
  - `azure_llm` – default assistant model.
  - `large_azure_llm` – optional higher-capacity model.
  - `gpt_oss_llm` – lightweight routing/database model.
- Required environment variables (examples):
  - `AZURE_OPENAI_ENDPOINT`
  - `AZURE_OPENAI_API_KEY`
  - `AZURE_OPENAI_API_VERSION`
  - `AZURE_OPENAI_DEPLOYMENT_NAME`
  - `GPT_OSS_DEPLOYMENT_NAME`
- Loaded via `.env` (root) using `python-dotenv` and Pydantic settings (`helpers/config.py`).

## REST API Reference

| Method | Endpoint | Description |
| ------ | -------- | ----------- |
| POST | `/api/personal_assistant/conversations/start` | Create conversation, return `conversation_id`. |
| POST | `/api/personal_assistant/analyze` | Submit user query, trigger orchestration, persist messages. |
| GET | `/api/database/messages` | Fetch conversation message history. |
| GET | `/api/database/conversations` | List conversations for a user. |
| GET | `/api/database/transactions` | Filterable transaction list. |
| GET | `/api/database/budget` | Budgets for user. |
| GET | `/api/database/income` | Income sources. |
| GET | `/api/database/goals` | User goals. |
| GET | `/api/database/users/{user_id}` | Single user profile. |
| GET | `/api/database/analytics/monthly-spend` | Monthly spend aggregate. |
| GET | `/api/database/analytics/overspend` | Current-month overspend report. |
| GET | `/api/database/analytics/income-total` | Income grouped by type & period. |
| POST | `/api/database/execute/select` | Execute read-only SQL (safeguarded to SELECT/WITH). |
| POST | `/api/database/execute/modify` | Execute INSERT/UPDATE/DELETE. |
| GET | `/api/personal_assistant/health` | Service health probe. |

## Running the System

1. **Install Python dependencies**
   - Root environment (agents + CLI): `pip install -r requirement.txt` *(typo in filename currently—rename if desired).*
   - API service: `pip install -r api/requirements.txt`.

2. **Configure environment**
   - `.env` at project root for Azure OpenAI and shared settings.
   - `.env` for the API (same root file is loaded by Django) with database credentials:
     ```
     DB_HOST=...
     DB_USER=...
     DB_PASSWORD=...
     DB_NAME=...
     DJANGO_SECRET_KEY=...
     ```

3. **Start services**
   - API: `python api/manage.py runserver 0.0.0.0:8000`.
   - CLI: `python main.py` (ensure API is reachable at `http://localhost:8000/api`).

4. **Interact**
   - Type prompts in the CLI.
   - Tables are printed when `data` is present.

5. **Optional: Production server**
   - Run `python api/run_server.py` (Waitress) for a threaded, Windows-friendly deployment.

## Testing & Troubleshooting
- No automated tests provided (`tests/test_workflow.py` is a placeholder). Recommend adding:
  - Unit tests for routing decisions (mock LLM).
  - Integration tests against API endpoints using a test database.
- Common issues:
  - Missing Azure OpenAI variables → LLM calls hang or fail.
  - Postgres connectivity → check `.env` values and DB availability.
  - Conversation history not updating → ensure `_store_messages_sync` inserts succeed; inspect Django logs.

## Extensibility Notes
- Additional agents under `agents/` can be integrated by expanding `main_graph.py` (add routing decisions and nodes).
- The behaviour analyst graph already supports iterative refinement via validation loops—extend with additional audit nodes if higher accuracy is required.
- `transaction_agent/` contains OCR/audio ingestion tooling that could feed additional data into the system; not currently wired into the orchestrator.

---
This document replaces legacy content with an up-to-date view of the multi-agent architecture, allowing developers to understand, operate, and extend the system effectively.
