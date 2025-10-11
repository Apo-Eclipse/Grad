from typing import TypedDict
from LLMs.ollama_llm import gpt_oss
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
------------------------------------------------------------
1. user_table
------------------------------------------------------------
Purpose: Stores demographic and socioeconomic information for each user.

Columns:
- User_ID (INT, PK, AUTO_INCREMENT): Unique identifier for each user.
- Name (VARCHAR(100)): User's full name.
- Age (INT): User's age in years.
- Gender (ENUM('Male','Female','Other')): Gender of the user.
- Job_Title (VARCHAR(100)): Current job title.
- Employment_Status (ENUM('Full-time','Part-time','Unemployed','Freelancer','Student')): Employment type.
- Education (VARCHAR(100)): Highest level of education completed.
- Marital_Status (ENUM('Single','Married','Divorced','Widowed')): Marital status.
- Address (VARCHAR(200)): Residential address (includes neighborhood and city).
- Income_EGP (DECIMAL(10,2)): Monthly income in Egyptian Pounds.

------------------------------------------------------------
2. transactions_table
------------------------------------------------------------
Purpose: Stores detailed records of every financial transaction for users.

Columns:
- Transaction_ID (INT, PK, AUTO_INCREMENT): Unique transaction identifier.
- User_ID (INT, FK → user_table.User_ID): Linked user.
- Category (VARCHAR(50)): Spending category (e.g., Groceries, Transport, Coffee).
- Store_Name (VARCHAR(100)): Vendor or service provider name.
- Day (TINYINT): Day of the month when the transaction occurred.
- Month (TINYINT): Month of the year when the transaction occurred.
- Year (SMALLINT): Year of the transaction.
- Name_of_day (ENUM('Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday')): Weekday name.
- Hour (TINYINT): Hour of the transaction (24-hour format).
- Minute (TINYINT): Minute of the transaction.
- Neighborhood (VARCHAR(100)): Neighborhood of the transaction.
- City (VARCHAR(100)): City of the transaction (e.g., Cairo, Giza).
- Amount_EGP (DECIMAL(10,2)): Transaction amount in Egyptian Pounds.
- Type_spending (ENUM('Cash','Credit','Debit','E-Wallet','Bank Transfer')): Payment method.

------------------------------------------------------------
3. budget_table
------------------------------------------------------------
Purpose: Tracks spending limits and monitoring for each user and category.

Columns:
- user_id (INT, FK → user_table.User_ID): Linked user.
- budget_name (VARCHAR(100)): Descriptive name for the budget (e.g., 'Groceries Budget Sep 2025').
- priority_level (ENUM('low','mid','high')): Importance of this budget.
- limit (DECIMAL(10,2)): Planned or allowed budget cap.
- description (TEXT): Short status text describing spending performance or targets.

------------------------------------------------------------
4. goals_table
------------------------------------------------------------
Purpose: Tracks long-term financial goals and progress for each user.

Columns:
- user_id (INT, FK → user_table.User_ID): Linked user.
- goal_name (VARCHAR(100)): Goal title (e.g., 'Emergency Fund').
- target_date (DATE): Date by which the user wants to reach the goal.
- target_saving (DECIMAL(10,2)): Total savings target in EGP.
- current (DECIMAL(10,2)): Current amount saved.
- objective (TEXT): Description of the goal.
- query_saving (VARCHAR(255)): Optional computed formula or query for dynamic savings tracking.

------------------------------------------------------------
Relationships:
- user_table (1) ───< transactions_table (many)
- user_table (1) ───< budget_table (many)
- user_table (1) ───< goals_table (many)

------------------------------------------------------------
Indexes and Keys:
- PK: user_table.User_ID, transactions_table.Transaction_ID
- FK: transactions_table.User_ID, budget_table.user_id, goals_table.user_id

------------------------------------------------------------
Notes:
- All monetary values are stored in Egyptian Pounds (EGP).
- Date and time fields enable fine-grained temporal analysis.
- The schema supports both behavioral analytics and personalized financial storytelling.
"""

user_prompt = """
Please validate the following:
User Query: {user_query}

Query Result: {query_result}

Explanation: {explanation}


"""
# 3. Create the Prompt Template
validation_prompt = ChatPromptTemplate.from_messages([
    ("system", validation_system_prompt),
    # The user message will contain the data to be validated
    ("user", user_prompt)
])

# 4. Build the final agent chain using LangChain Expression Language (LCEL)
ValidationAgent = validation_prompt | large_azure_llm.with_structured_output(ValidationAgentOutput, method="function_calling")
