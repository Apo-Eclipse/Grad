from typing import TypedDict
from LLMs.gemini_models import gemini_llm
from langchain_core.prompts import ChatPromptTemplate
from pydantic import Field, BaseModel

class ExplainerAgentOutput(BaseModel):
    explanation: str = Field(..., description="The explanation in plain text")

system_prompt = """
You are an explainer_agent.
Your task is to translate the table data into a human-readable format.
You will be given the request made to the database_agent and the table it returned.
like this:
"The request was: i want to see all transactions made in the last month
The result was: [{{"date": "2023-05-01", "amount": 100, "type": "credit"}}, {{"date": "2023-05-15", "amount": 50, "type": "debit"}}]"

Rules:
    1. Always respond in plain text.
    2. Do not include SQL queries, JSON, or any structured format.
    3. Provide clear and concise explanations of the data.
    4. If the table is empty, respond with "No data found."
    5. Explain all rows in the table, but you may **group rows that share the same category or pattern** 
        into a single explanation to avoid repetition.
        - For example, if several consecutive rows show "Groceries" as the top category, 
            you can describe them together instead of one by one.
    6. Always make sure that no row is ignored. Every row must be represented in the explanation,
        either individually or as part of a grouped explanation.
    7. After covering all rows, you may provide an overall summary or trend analysis.

Example 1 (different categories):
If the request was: 
    "i want to see all transactions made in the last month"
And the result was: 
    [{{"date": "2023-05-01", "amount": 100, "type": "credit"}}, {{"date": "2023-05-15", "amount": 50, "type": "debit"}}]

You should respond with:
    "The table shows two transactions made in the last month. 
    The first transaction was a credit of 100 Egyptian Pounds on May 1, 2023. 
    The second transaction was a debit of 50 Egyptian Pounds on May 15, 2023. 
    Overall, this indicates that there was more money credited than debited during this period."

Example 2 (grouping similar rows):
If the request was:
    "i want to see the top spending categories per hour"
And the result was:
    [{{"hour": 7, "category": "Groceries", "amount": 5237}},
    {{"hour": 8, "category": "Groceries", "amount": 1112}},
    {{"hour": 9, "category": "Groceries", "amount": 2220}},
    {{"hour": 10, "category": "Groceries", "amount": 3178}},
    {{"hour": 11, "category": "Entertainment", "amount": 742}}]

You should respond with:
    "From 7:00 to 10:00, groceries were consistently the top spending category, 
    ranging from 1,112 to 5,237 Egyptian Pounds. 
    At 11:00, entertainment became the leading category with 742 Egyptian Pounds. 
    This shows that groceries dominate the early morning hours, with entertainment taking over later."
"""


meta_data = metadata = """
        That database that the tables are extracted from contains two main
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
            Category       → Spending category (e.g., Groceries, Transport),
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
    ("system", meta_data),
    ("user", "{request}")
])

gemini_llm1 = gemini_llm
gemini_llm1.temperature = 0.4
Explainer_agent = prompt | gemini_llm1.with_structured_output(ExplainerAgentOutput)