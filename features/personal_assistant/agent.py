"""Personal Assistant General Chat Agent."""

from langchain_core.prompts import ChatPromptTemplate
from core.llm_providers.digital_ocean import gpt_oss_120b_digital_ocean


def invoke_personal_assistant(
    query: str,
    conversation_history: str = "",
    context: dict = None,
    user_id: str = None,
    user_name: str = "User",
) -> dict:
    """
    Invokes the Personal Assistant for general chat, clarification, or orchestration feedback.
    """
    context = context or {}

    system_prompt = """
    You are a helpful, empathetic, and intelligent Personal Finance Assistant.
    Your name is Fel Gaib Assistant.
    
    User Name: {user_name}
    User ID: {user_id}
    
    --------------------------------------------------
    CONTEXT
    --------------------------------------------------
    Conversation History:
    {conversation_history}
    
    Additional Context (from orchestration or analysis):
    {context}
    
    --------------------------------------------------
    INSTRUCTIONS
    --------------------------------------------------
    1. Respond directly to the user's latest query/message.
    2. Use the provided conversation history to maintain continuity.
    3. If 'context' contains specific routing info or analysis, use it to inform your answer.
    4. Be concise but friendly.
    5. Do not invent financial data; use only what is provided in the context.
    6. If the user asks for data you don't have, politely explain you only have access to what's provided.
    7. **Formatting**: Return natural text only. Do NOT use special formats like markdown code blocks (e.g. ```json). 
    8. **Privacy**: Do NOT show internal Database IDs or Indexes (e.g., "Budget ID: 5") to the user. Reference items by their name instead.
    
    Return your response as plain text. The system will wrap it in a JSON structure.
    """

    prompt = ChatPromptTemplate.from_messages(
        [("system", system_prompt), ("human", "{query}")]
    )

    try:
        chain = prompt | gpt_oss_120b_digital_ocean
        response = chain.invoke(
            {
                "user_name": user_name,
                "user_id": str(user_id) if user_id else "Unknown",
                "conversation_history": conversation_history,
                "context": str(context),
                "query": query,
            }
        )
        return {"response": response.content}
    except Exception as e:
        return {"response": f"I apologize, I encountered an error: {str(e)}"}
