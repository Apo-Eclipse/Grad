from langchain_core.prompts import ChatPromptTemplate
from core.llm_providers.digital_ocean import gpt_oss_120b_digital_ocean
from pydantic import BaseModel, Field
from core.utils.dynamic_db_schema import get_dynamic_schema


# 1. Define the Structured Output using Pydantic
class ValidationAgentOutput(BaseModel):
    """
    Defines the structured output for the Validation Agent.
    """

    valid: bool = Field(
        ...,
        description="True if the explanation perfectly matches the data, False otherwise.",
    )
    reasoning: str = Field(
        ...,
        description="The specific reason for failure if invalid, otherwise an empty string.",
    )


# 2. Create the System Prompt with clear instructions and examples
validation_system_prompt = r"""
You are a meticulous Validation Agent. Your mission is to verify if a given explanation is a perfect, one-to-one representation of a query_result, containing all of its information and nothing more.
# You will be provided with two inputs:
1-query_result: The source of truth, typically a dictionary or list of dictionaries.
2-explanation: A natural language text that purports to describe the query_result.

# Core Directives
## You must evaluate the explanation against the query_result based on the following directives:

### Special Case: Empty or No Data
- If the query_result is empty (empty list [], empty dict {{}}, None, or no data), the explanation is AUTOMATICALLY VALID as long as it acknowledges the absence of data.
- Examples of valid explanations for empty results:
  * "No transactions found"
  * "There are no records matching this query"
  * "The query returned no results"
- Return {{"valid": true, "reasoning": ""}} for any reasonable acknowledgment of no data.

### For Non-Empty Data:
1-No Omissions (Completeness): The explanation must explicitly mention every single piece of data (all keys and their corresponding values) found in the query_result. No data from the source can be ignored or left out.
2-No Hallucinations (Strict Grounding): The explanation must only contain information that is explicitly present in the query_result. Do not infer, calculate, or add any external details. Every fact, number, and name must be directly traceable to the source data.

### Output Format
You MUST respond in a single JSON object with two fields: `valid` (boolean) and `reasoning` (string).

- If the explanation is a perfect representation of the data, return:
{{"valid": true, "reasoning": ""}}

- If the explanation is incorrect, incomplete, or adds extra details, return:
{{"valid": false, "reasoning": "Your specific reason here."}}

# --- Database schema reference (updated; for context only) ---
{schema}
# --- End of database schema reference ---
note : all money amounts are in EGP currency.
"""

# 3. Create the Prompt Template
validation_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", validation_system_prompt),
        # The user message will contain the data to be validated
        (
            "user",
            "Please validate the following:\n\nQuery Result:\n{query_result}\n\nExplanation:\n`{explanation}`",
        ),
    ]
).partial(schema=get_dynamic_schema())

# 4. Build the final agent chain using LangChain Expression Language (LCEL)
ValidationAgent = validation_prompt | gpt_oss_120b_digital_ocean.with_structured_output(
    ValidationAgentOutput, method="function_calling"
)
