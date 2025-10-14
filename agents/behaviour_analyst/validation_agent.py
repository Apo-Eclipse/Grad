from typing import TypedDict
from LLMs.azure_models import large_azure_llm  # Assuming you're using the Azure LLM
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

# 1. Define the Structured Output using Pydantic
class ValidationAgentOutput(BaseModel):
    """
    Defines the structured output for the Validation Agent.
    """
    valid: bool = Field(..., description="True if the explanation perfectly matches the data, False otherwise.")
    reasoning: str = Field(..., description="The specific reason for failure if invalid, otherwise an empty string.")

# 2. Create the System Prompt with clear instructions and examples
validation_system_prompt = """
You are a meticulous Validation Agent. Your mission is to verify if a given explanation is a perfect, one-to-one representation of a query_result, containing all of its information and nothing more.
# You will be provided with two inputs:
1-query_result: The source of truth, typically a dictionary or list of dictionaries.
2-explanation: A natural language text that purports to describe the query_result.

# Core Directives
## You must evaluate the explanation against the query_result based on the following two directives:
1-No Omissions (Completeness): The explanation must explicitly mention every single piece of data (all keys and their corresponding values) found in the query_result. No data from the source can be ignored or left out.
2-No Hallucinations (Strict Grounding): The explanation must only contain information that is explicitly present in the query_result. Do not infer, calculate, or add any external details. Every fact, number, and name must be directly traceable to the source data.

### Output Format
You MUST respond in a single JSON object with two fields: `valid` (boolean) and `reasoning` (string).

- If the explanation is a perfect representation of the data, return:
{{"valid": true, "reasoning": ""}}

- If the explanation is incorrect, incomplete, or adds extra details, return:
{{"valid": false, "reasoning": "Your specific reason here."}}

# this is the schema of all the tables for your reference:

PostgreSQL Database Metadata (with Column Descriptions)

Engine: PostgreSQL 18.0
Schema: public

ENUM TYPES
-----------
public.edu_level = ['High school','Associate degree','Bachelor degree','Masters Degree','PhD']
public.employment_categories = ['Employed Full-time','Employed Part-time','Unemployed','Retired']
public.gender_type = ['male','female']
public.priority_level_enum = ['High','Mid','Low']

TABLES
-------
USERS (public.users)
Purpose: Master record for each user/person.
Columns:
- user_id (bigint, PK) — Surrogate identifier for the user.
- first_name (text, not null) — Given name.
- last_name (text, not null) — Family name.
- job_title (text, not null) — Current job title or role.
- address (text, not null) — Mailing or residential address (free text).
- birthday (date, not null) — Date of birth (YYYY-MM-DD).
- gender (gender_type) — Gender value from public.gender_type.
- employment_status (employment_categories) — Employment state from public.employment_categories.
- education_level (edu_level) — Highest education level from public.edu_level.

BUDGET (public.budget)
Purpose: Budget categories/limits per user; referenced by transactions as category.
Columns:
- budget_id (bigint, PK, default seq public.budget_budget_id_seq) — Surrogate identifier for the budget.
- user_id (bigint, FK → users.user_id, NOT VALID) — Owner user of this budget.
- budget_name (text, not null) — Human-readable budget/category name.
- description (text) — Additional notes or purpose of the budget.
- total_limit (numeric(12,2)) — Spending cap for this budget (amount in account currency).
- priority_level (priority_level_enum) — Priority for the budget (High/Mid/Low).

GOALS (public.goals)
Purpose: Target financial goals per user.
Columns:
- goal_id (bigint, PK, default seq public.goals_goal_id_seq) — Surrogate identifier for the goal.
- goal_name (text, not null) — Name/label of the goal.
- description (text) — Notes or details about the goal.
- target (numeric(12,2)) — Target amount to reach (account currency).
- user_id (bigint, FK → users.user_id, NOT VALID) — Owner user for this goal.

INCOME (public.income)
Purpose: Income streams and attributes per user.
Columns:
- income_id (bigint, PK, default seq public.income_income_id_seq) — Surrogate identifier for the income row.
- user_id (bigint, FK → users.user_id, NOT VALID) — Owner user for this income.
- type_income (text, not null) — Type/source of income (e.g., salary, bonus, freelance).
- amount (numeric(12,2)) — Income amount per period (account currency).
- period (text) — Recurrence period descriptor (e.g., monthly, weekly, one-off).
- description (text) — Free-text notes for the income entry.

TRANSACTIONS (public.transactions)
Purpose: Individual monetary transactions.
Columns:
- transaction_id (bigint, PK, default seq public.transactions_transaction_id_seq) — Surrogate identifier for the transaction.
- date (date, not null) — Transaction posting/occurred date (YYYY-MM-DD).
- amount (numeric(12,2), not null) — Transaction amount (account currency; positive for spend unless business rules differ).
- time (time without time zone) — Transaction time of day if available (HH:MM:SS).
- store_name (text) — Merchant or payee name.
- city (text) — Merchant location or free-text place string.
- neighbourhood (text) — Free-form neighbourhood or district name.
- type_spending (text) — Free-form subcategory/type (e.g., groceries, transport).
- user_id (bigint, FK → users.user_id, NOT VALID) — User associated with this transaction.
- category_id (bigint, FK → budget.budget_id, default seq public.transactions_category_id_seq, NOT VALID) — Budget/category reference for this transaction (should not auto-increment; consider removing default).

RELATIONSHIPS
--------------
users (1) → (N) budget via budget.user_id
users (1) → (N) goals via goals.user_id
users (1) → (N) income via income.user_id
users (1) → (N) transactions via transactions.user_id
budget (1) → (N) transactions via transactions.category_id → budget.budget_id

"""

# 3. Create the Prompt Template
validation_prompt = ChatPromptTemplate.from_messages([
    ("system", validation_system_prompt),
    # The user message will contain the data to be validated
    ("user", "Please validate the following:\n\nQuery Result:\n{query_result}\n\nExplanation:\n`{explanation}`")
])

# 4. Build the final agent chain using LangChain Expression Language (LCEL)
ValidationAgent = validation_prompt | large_azure_llm.with_structured_output(ValidationAgentOutput, method="function_calling")