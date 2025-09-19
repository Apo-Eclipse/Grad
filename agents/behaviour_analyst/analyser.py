from typing import TypedDict
from LLMs.gemini_models import gemini_llm
from langchain_core.prompts import ChatPromptTemplate
from pydantic import Field, BaseModel

class AnalyserOutput(BaseModel):
    output: str = Field(..., description="The analysis output from the agent.")
    message : str = Field(..., description="Any additional message or insights from the analysis to the orchestrator.")
    
system_prompt = """
    You are the analyser Agent.
    Your task is to analyze the spending behavior of a user based on text explain tables data acquired from previous queries.
    You have to return a summary of the analysis and any insights you can derive from the data.
    
    ### Rules
    1. Focus on the user's spending patterns, habits, and any anomalies you can identify.
    2. Use the data acquired to provide a comprehensive analysis.
    3. Ensure your analysis is clear, concise, and actionable.
    4. If the data is insufficient, indicate what additional information would be helpful.
    5. Try to understand user's behavior in terms of time, location, store, and category.
    6. If their needed any further analysis, please indicate that in the message field.
    7. Give message to the orchestrator telling them if you need more data or not and what you have done.
    8. Provide your response in the following JSON format:
    {{
        "message": "<Any additional message or insights>"
        "output": "<Your analysis here>",
    }}
    9. Try to request more data if needed for better analysis such as more analysis on specific category or store or location or time.
"""
metadata = """ 
    That are the data we have acquired from the database:
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
analyser_prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("user", metadata),
    ("user", "Acquired Data: {data_acquired}")
])

Analyser = analyser_prompt | gemini_llm.with_structured_output(AnalyserOutput)