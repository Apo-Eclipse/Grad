from ninja import NinjaAPI

# Import Assistant Routers
from personal_assistant_api.assistants.api import router as assistant_router
from personal_assistant_api.assistants.conversations import (
    router as conversations_router,
)
from personal_assistant_api.goal_maker.api import router as goal_maker_router
from personal_assistant_api.budget_maker.api import router as budget_maker_router
from personal_assistant_api.transaction_maker.api import (
    router as transaction_maker_router,
)

# Import Database Routers
from personal_assistant_api.database.transactions import router as transactions_router
from personal_assistant_api.database.budgets import router as budgets_router
from personal_assistant_api.database.goals import router as goals_router
from personal_assistant_api.database.users import router as users_router
from personal_assistant_api.database.income import router as income_router
from personal_assistant_api.database.conversations import (
    router as db_conversations_router,
)
from personal_assistant_api.database.analytics import router as analytics_router

api = NinjaAPI(
    title="Personal Assistant API",
    version="2.0.0",
    description="API for interacting with the Multi-Agent Personal Assistant system (Modular)",
    docs_url="docs",
)

# Assistant Endpoints
api.add_router("personal_assistant/", assistant_router, tags=["Personal Assistant"])
api.add_router(
    "personal_assistant/conversations/",
    conversations_router,
    tags=["Conversations (Manual)"],
)
api.add_router("personal_assistant/goals/", goal_maker_router, tags=["Goal Maker"])
api.add_router("personal_assistant/budget/", budget_maker_router, tags=["Budget Maker"])
api.add_router(
    "personal_assistant/transaction/",
    transaction_maker_router,
    tags=["Transaction Maker"],
)

# Database Endpoints (CRUD)
api.add_router(
    "database/transactions/", transactions_router, tags=["Database - Transactions"]
)
api.add_router("database/budgets/", budgets_router, tags=["Database - Budgets"])
api.add_router("database/goals/", goals_router, tags=["Database - Goals"])
api.add_router("database/users/", users_router, tags=["Database - Users"])
api.add_router("database/income/", income_router, tags=["Database - Income"])
api.add_router(
    "database/conversations/",
    db_conversations_router,
    tags=["Database - Conversations"],
)
api.add_router("database/analytics/", analytics_router, tags=["Database - Analytics"])
