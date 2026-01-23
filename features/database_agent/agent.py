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

COMMON PATTERNS:
- Monthly spend by budget:
  SELECT b.budget_name, DATE_TRUNC('month', t.date) AS month, ROUND(SUM(t.amount)::numeric, 2) AS total_spent
  FROM transactions t JOIN budget b ON t.budget_id = b.budget_id
  WHERE t.user_id = $USER_ID GROUP BY b.budget_name, month ORDER BY month DESC

- Overspend detection:
  SELECT b.budget_name, ROUND(SUM(t.amount)::numeric, 2) AS spent, b.total_limit,
  ROUND(100.0 * SUM(t.amount) / NULLIF(b.total_limit, 0), 2) AS pct_of_limit
  FROM transactions t JOIN budget b ON t.budget_id = b.budget_id
  WHERE t.user_id = $USER_ID AND DATE_TRUNC('month', t.date) = DATE_TRUNC('month', CURRENT_DATE)
  GROUP BY b.budget_name, b.total_limit ORDER BY pct_of_limit DESC
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
