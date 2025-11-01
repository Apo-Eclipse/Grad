**Executive Summary**
- Django + Ninja REST API serving a multi-agent Personal Assistant.
- Async endpoints orchestrate LangGraph agents, persist conversations, and expose domain data.
- Defaults emphasize safety: parameterized SQL, guarded write routes, validated schemas, and consistent logging.

**Entry Points**
- Base path: `/api/`
- Docs UI: `/api/docs`
- Hosted demo: `https://grad-pth6g.ondigitalocean.app/api`
- Routers:
  - `/api/personal_assistant/*` (api/personal_assistant_api/api.py)
  - `/api/database/*` (api/personal_assistant_api/db_retrieval.py)

**Directory Layout**
- `api/api_config`: Django project wiring (settings, URLs, ASGI/WSGI).
- `api/personal_assistant_api`: Endpoints, services, and schemas.
- `api/run_server.py`: Production entry (Waitress WSGI).
- `api/requirements.txt`: API dependencies.

**Modules**
- `api/personal_assistant_api/api.py`
  - Conversation endpoints: start session, analyze query, health.
  - `_insert_chat_message` centralizes `chat_messages` inserts.
  - `_store_messages_sync` records user/assistant messages and optional JSON data; updates `chat_conversations.last_message_at`.
- `api/personal_assistant_api/services.py`
  - `PersonalAssistantService` lazily loads `graphs.main_graph.main_orchestrator_graph`.
  - `run_analysis` handles async (`ainvoke`) and sync (`invoke` in executor) orchestrators and normalizes results.
- `api/personal_assistant_api/db_retrieval.py`
  - `_run_select`, `_safe_json_body`, `_data_response` standardize query execution and responses.
  - Data and analytics endpoints for transactions, budgets, messages, and guarded custom SQL.
- `api/personal_assistant_api/schemas.py`
  - Pydantic schemas for request/response validation and OpenAPI.

**Endpoints**
- Personal Assistant
  - POST `/api/personal_assistant/conversations/start` - start a session
  - POST `/api/personal_assistant/analyze` - run analysis and persist messages
  - GET  `/api/personal_assistant/health` - health check
- Database
  - GET  `/api/database/transactions?user_id=&start_date=&end_date=&limit=`
  - GET  `/api/database/budget?user_id=`
  - GET  `/api/database/users/{user_id}`
  - GET  `/api/database/income?user_id=`
  - GET  `/api/database/goals?user_id=&status=`
  - GET  `/api/database/conversations?user_id=&limit=`
  - GET  `/api/database/messages?conversation_id=&limit=`
  - GET  `/api/database/analytics/monthly-spend?user_id=`
  - GET  `/api/database/analytics/overspend?user_id=`
  - GET  `/api/database/analytics/income-total?user_id=`
  - POST `/api/database/execute/select` - guarded SELECT/CTE with optional `limit`
  - POST `/api/database/execute/modify` - guarded INSERT/UPDATE/DELETE

**Request Lifecycle**
- `analyze` validates payloads, enriches metadata with `conversation_id` and `user_id`.
- Service composes orchestrator input and calls LangGraph:
  - If `ainvoke` exists, await it; otherwise offload `invoke` to a thread via `run_in_executor`.
  - Result typically includes `final_output`, optional `data`, `has_data`, and `agents_used`.
- On success, `_store_messages_sync` persists the user input, assistant output, and JSON data (if any).
- Response returns `final_output` and, when present, `data` and `conversation_id`.

**Schemas**
- `AnalysisRequestSchema` (`api/personal_assistant_api/schemas.py:8`)
  - `query` (str, required): the natural-language request to analyze.
  - `filters` (dict, optional): additional structured hints passed through to agents.
  - `metadata` (dict, optional, defaults to empty dict): caller-supplied context; `conversation_id`/`user_id` are copied from here if not sent at the top level.
  - `conversation_id` (int, optional): binds the request to an existing conversation.
  - `user_id` (int, optional): identifies the end user; defaults to `"3"` inside the service if omitted.
- `AnalysisResponseSchema` (`api/personal_assistant_api/schemas.py:16`)
  - `final_output` (str, required): assistant text shown to the user.
  - `data` (any, optional): structured payload (table/list/dict) for UI rendering.
  - `conversation_id` (int, optional): echo of the conversation identifier for convenience.
- `AnalysisErrorSchema` (`api/personal_assistant_api/schemas.py:22`)
  - `error` (str): stable error code such as `INVALID_QUERY` or `ANALYSIS_ERROR`.
  - `message` (str): human-readable explanation.
  - `timestamp` (datetime): populated automatically with `datetime.now()` when the error is emitted.
- `ConversationStartSchema` (`api/personal_assistant_api/schemas.py:28`)
  - `user_id` (int, required): person initiating the conversation.
  - `channel` (str, optional): defaults to `"web"`; use to distinguish surfaces (mobile, kiosk, etc.).
- `ConversationResponseSchema` (`api/personal_assistant_api/schemas.py:33`)
  - `conversation_id` (int): newly created identifier.
  - `user_id` (int): mirrors the caller-supplied user id.
  - `channel` (str): channel used for the conversation.
  - `started_at` (datetime): timestamp of conversation creation.

**Asynchrony And Performance**
- Async `analyze` endpoint keeps the server responsive during long operations.
- Service supports async and sync orchestrators without changing API code.
- DB writes from async code use `sync_to_async` to run safely in a thread pool.

**Data Persistence**
- `chat_conversations` stores session metadata and last activity.
- `chat_messages` stores a full audit trail: `sender_type`, `source_agent`, `content`, `content_type` (`text` or `json`).
- Queries are parameterized to mitigate injection risk.

**Security Controls**
- `execute/select` only accepts `SELECT` or `WITH`, auto-adds `LIMIT` if missing.
- `execute/modify` only accepts `INSERT`, `UPDATE`, `DELETE`.
- Errors are logged with stack traces; clients receive structured error envelopes.

**Observability**
- Structured logging during initialization, analysis, and persistence.
- Suitable for centralized log shipping; consider request or conversation IDs in production logging.

**Configuration And Operations**
- Environment variables (example): `DJANGO_SECRET_KEY`, `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`.
- Development: `python manage.py runserver 0.0.0.0:8000`.
- Production: `python run_server.py` (Waitress WSGI).
- OpenAPI docs: `http://localhost:8000/api/docs`.

**Change Log Alignment**
- Centralized message inserts via `_insert_chat_message`.
- DB retrieval unified with `_run_select` and safe JSON parsing.
- Service uses `time.perf_counter()` and explicit orchestrator guards.

**Roadmap Suggestions**
- Add correlation IDs across layers for end-to-end tracing.
- Add pagination cursors for messages and transactions.
- Add rate limits to `/execute/*` endpoints as a defense in depth.
