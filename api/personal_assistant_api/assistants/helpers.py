from personal_assistant_api.core.database import run_select

def get_user_summary(user_id: int):
    """Get a summary of user data for context."""
    user = run_select("SELECT * FROM users WHERE user_id = %s", [user_id])
    if not user:
        return None
    return user[0]

def get_recent_conversations(user_id: int, limit: int = 5):
    """Get recent conversations for context."""
    sql = "SELECT * FROM conversations WHERE user_id = %s ORDER BY created_at DESC LIMIT %s"
    return run_select(sql, [user_id, limit])
