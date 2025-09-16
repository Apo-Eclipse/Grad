from typing import TypedDict
from LLMs.gemini_models import gemini_llm
from LLMs.azure_models import azure_llm
from langchain_core.prompts import ChatPromptTemplate
from pydantic import Field, BaseModel
import sqlite3

conn = sqlite3.connect("D:/projects/Multi-Agent System/data/database.db")

class DatabaseAgentOutput(BaseModel):
    final_output: str = Field(..., description="The SQL query in JSON format")

system_prompt = """
You are a database_agent.
Your task is to translate a single natural language step into one valid SQLite query.

Rules:
    1. Only respond with ONE SQL query per request.
    2. Output must always be a single JSON object:
    {{
        "step": "the step as plain text",
        "query": "the SQL query"
    }}
    3. Do not include explanations, comments, or multiple queries.
    4. SQL must be valid SQLite syntax.
    5. Use single quotes inside the SQL, double quotes for JSON.
    6. Do NOT generate UPDATE or DELETE queries. If asked, respond with:
        {{"step": "error", "query": "Query rejected"}}
    7. If you cannot generate a query, return:
        {{"step": "error", "query": "Query rejected"}}

Date and Time Handling:
    - Use the structured fields directly:
        * Day, Month, Year for calendar values
        * Name_of_day for weekday (e.g., Monday, Tuesday)
        * Hour and Minute for time-of-day analysis
    - Do not reference the raw DateTime column.

Grouping and Ranking (SQLite-safe):
    - For "most frequent", "top", or "highest" results:
        * Always compute aggregates with GROUP BY.
        * Then restrict results to ONLY the maximum value(s) per group.
        * If multiple results tie for maximum, return all of them.
    - Never just use ORDER BY to imply "top".
    - In SQLite, enforce this with:
        * Subquery + MAX() joined back to the grouped results (always works), OR
        * Window functions (RANK, ROW_NUMBER, DENSE_RANK) if supported.
"""



metadata = """
Tables:
- user_table(
    User_ID           → Unique identifier for each user,
    Name              → User's full name,
    Age               → User's age in years,
    Gender            → User's gender,
    Job_Title         → Current job title,
    Employment_Status → Employment type (e.g., Full-time, Part-time, Unemployed),
    Education         → Highest level of education completed,
    Marital_Status    → User's marital status,
    Address           → Residential address (includes neighborhood/city),
    Income_EGP        → Monthly income in Egyptian Pounds
)

- transactions_table(
    Transaction_ID → Unique identifier for each transaction,
    User_ID        → Foreign key referencing user_table(ID),
    Category       → Spending category (e.g., Groceries, Transport, Coffee),
    Store_Name     → Name of the store or service provider,
    Day            → Day of the month when the transaction occurred,
    Month          → Month of the year when the transaction occurred,
    Year           → Year of the transaction,
    Name_of_day    → Name of the weekday (e.g., Monday, Tuesday),
    Hour           → Hour of the transaction (24-hour format),
    Minute         → Minute of the transaction,
    Neighborhood   → Neighborhood where the transaction took place,
    City           → City of the transaction (e.g., Cairo, Giza),
    Amount_EGP     → Transaction amount in Egyptian Pounds,
    Type_spending  → Payment method used (e.g., Cash, Credit, E-Wallet)
)
"""

prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("user", metadata),
    ("user", "{request}")
])
gemini_llm2 = gemini_llm
gemini_llm2.temperature = 0

DatabaseAgent = prompt | gemini_llm2.with_structured_output(DatabaseAgentOutput)