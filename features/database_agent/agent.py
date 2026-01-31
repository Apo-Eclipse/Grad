from core.llm_providers.digital_ocean import gpt_oss_120b_digital_ocean
from langchain_core.prompts import ChatPromptTemplate
from pydantic import Field, BaseModel
from core.utils.dynamic_db_schema import get_dynamic_schema


class DatabaseAgentOutput(BaseModel):
    query: str = Field(..., description="The corresponding SQL query")
    edit: bool = Field(
        False,
        description="Whether the query is an edit/DDL/DML that should be executed",
    )
    message: str = Field(
        ...,
        description="A natural language message to the user/orchestrator (e.g., validation error or confirmation)",
    )


system_prompt = """
You are a read-only database agent. Translate requests into a single PostgreSQL query.

OUTPUT: {{"query": "<SQL>", "edit": false, "message": "<TEXT>"}}
- "message": Brief confirmation (success) or explanation (error).
- "query": Empty string "" if error/invalid.

RULES:
1. **STRICT READ-ONLY**: NO INSERT, UPDATE, DELETE, DROP.
2. **PostgreSQL Syntax**: Use DATE_TRUNC, EXTRACT, etc.
3. **Format**: Use column names (not indices) in results. Round numerics to 2 decimals.
4. **Context**: Always filter by `user_id`.
5. **Active Data Only**: If a table has an `active` column, YOU MUST include `AND active = true` in your WHERE clause to exclude soft-deleted records.

DATABASE SCHEMA (with field types):

{schema}

**CRITICAL: FOREIGN KEYS**
- The schema uses Django conventions.
- Foreign Key columns ALWAYS end in `_id`.
- **DO NOT** select `budget`, `account`, `user`.
- **YOU MUST SELECT** `budget_id`, `account_id`, `user_id`.
- e.g. `SELECT budget_id FROM core_transaction` (CORRECT) vs `SELECT budget ...` (WRONG).
"""

user_prompt = """
request: {request}
user_id: {user_id}
"""

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_prompt),
        ("user", user_prompt),
    ]
).partial(schema=get_dynamic_schema())

DatabaseAgent = prompt | gpt_oss_120b_digital_ocean.with_structured_output(
    DatabaseAgentOutput
)
