# API Reference

**Base URL**: `http://localhost:8000/api`
**Version**: 1.0.0
**Auth**: Bearer Token (JWT) is required for most endpoints.

---

## 🔐 Authentication

### Login
**POST** `/auth/login`
Authenticate user with email and password to obtain access/refresh tokens.

**Request Body** (`LoginSchema`):
```json
{
  "email": "user@example.com",
  "password": "yourpassword"
}
```

**Response** (`TokenSchema`):
```json
{
  "access": "<access_token_string>",
  "refresh": "<refresh_token_string>",
  "user_id": 1,
  "email": "user@example.com"
}
```

### Refresh Token
**POST** `/auth/refresh`
Obtain a new access token using a valid refresh token.

**Request Body** (`RefreshSchema`):
```json
{
  "refresh": "<valid_refresh_token>"
}
```

**Response** (`TokenSchema`):
```json
{
  "access": "<new_access_token>",
  "refresh": "<original_or_new_refresh_token>",
  "user_id": 1,
  "email": "user@example.com"
}
```

---

## 🤖 Personal Assistant

### Analyze Request
**POST** `/personal_assistant/analyze`
**Personal Assistant Agent**: A specialized agent that acts as the analysis and retrieval interface. It communicates **only** with the **Behaviour Analyst** (for deep insights) and the **Database Agent** (for read-only data). It does not perform general system orchestration capabilities beyond this scope. Its primary focus is interpreting user intent for analysis and delivering clear, empathetic responses.

**Request Body** (`AnalysisRequestSchema`):
```json
{
  "query": "How much did I spend on food this month?",
  "conversation_id": 12, // Optional: default created if null
  "filters": {},         // Optional: pre-filter data
  "metadata": {}         // Optional: extra context
}
```

**Response** (`AnalysisResponseSchema`):
```json
{
  "final_output": "You spent 500 EGP on food.",
  "data": null,          // Optional: structured data payload
  "conversation_id": 12
}
```

### Budget Maker Assistant
**POST** `/personal_assistant/budget/assist`
Direct interaction with the Budget Maker agent.

**Request Body** (`BudgetMakerRequestSchema`):
```json
{
  "user_request": "Create a budget for Groceries of 3000 EGP",
  "conversation_id": 12 // Optional
}
```

**Response** (`BudgetMakerResponseSchema`):
```json
{
  "conversation_id": 12,
  "message": "Budget 'Groceries' created successfully.",
  "action": "create", // "create" or "update"
  "budget_name": "Groceries",
  "budget_id": 5,
  "total_limit": 3000.0,
  "description": "Monthly grocery budget",
  "priority_level_int": 1,
  "is_done": true
}
```

### Goal Maker Assistant
**POST** `/personal_assistant/goal/assist`
Direct interaction with the Goal Maker agent.

**Request Body** (`GoalMakerRequestSchema`):
```json
{
  "user_request": "I want to save for a Laptop",
  "conversation_id": 12 // Optional
}
```

**Response** (`GoalMakerResponseSchema`):
```json
{
  "conversation_id": 12,
  "message": "What is your target amount?",
  "action": "create",
  "goal_name": "Laptop",
  "goal_id": 10,
  "target": 0.0,
  "goal_description": null,
  "due_date": null,
  "plan": null,
  "is_done": false // True when goal is fully defined
}
```



---

## 📊 Dashboard

### Get Budgets
**GET** `/dashboard/budgets`
Returns active budgets with calculated spending progress for the current month.

**Response** (`List[DashboardBudgetSchema]`):
```json
[
  {
    "id": 1,
    "name": "Groceries",
    "description": "Monthly food",
    "priority": 1,
    "limit": 3000.0,
    "spent": 1500.0,
    "remaining": 1500.0,
    "percentage_used": 50.0,
    "color": "#3162ff",
    "icon": "wallet"
  }
]
```

### Get Summary
**GET** `/dashboard/summary`
Returns the user's financial net position for the current month.

**Response** (`DashboardSummarySchema`):
```json
{
  "total_income": 10000.0,
  "total_spent": 5000.0,
  "net_position": 5000.0,
  "is_deficit": false,
  "month_label": "October 2025"
}
```

---

## 🔔 Notifications

### List Notifications
**GET** `/notifications/`
List all notifications for the user, newest first.

**Response** (`List[NotificationSchema]`):
```json
[
    {
        "id": 1,
        "title": "Budget Alert",
        "message": "You exceeded your budget.",
        "is_read": false,
        "notification_type": "budget_alert",
        "created_at": "2025-10-27T10:00:00Z"
    }
]
```

### Mark as Read
**PUT** `/notifications/{notification_id}/read`
Mark a specific notification as read.

**Response**:
```json
"Marked as read"
```

---

## 🗄️ Database CRUD

### 👤 Users

#### Get User Profile
**GET** `/database/user/`

**Response** (`UserResponse`):
```json
{
  "status": "success",
  "message": "Success",
  "data": {
    "user_id": 1,
    "first_name": "John",
    "last_name": "Doe",
    "email": "user@example.com",
    "job_title": "Engineer",
    "address": "123 Main St",
    "birthday": "1990-01-01",
    "gender": "male",
    "employment_status": "Employed Full-time",
    "education_level": "Bachelor degree",
    "created_at": "2025-01-01T00:00:00Z"
  }
}
```

#### Register User
**POST** `/database/user/`

**Request Body** (`UserRegistrationSchema`):
```json
{
  "email": "user@example.com",
  "username": "user1",
  "password": "securepassword",
  "first_name": "John",
  "last_name": "Doe",
  "job_title": "Dev",          // Optional
  "address": "Cairo",          // Optional
  "birthday": "1990-01-01",    // Optional
  "gender": "male",            // Optional
  "employment_status": "Employed Full-time", // Optional
  "education_level": "Bachelor degree"       // Optional
}
```

**Response** (`UserResponse`):
```json
{
  "status": "success",
  "message": "User registered successfully",
  "data": {
    "user_id": 1,
    "first_name": "John",
    "last_name": "Doe",
    "email": "user@example.com",
    ...
  }
}
```

### 💰 Accounts

#### List Accounts
**GET** `/database/account/?type=REGULAR`

**Response** (`List[AccountSchema]`):
```json
[
  {
    "id": 1,
    "name": "Main Bank",
    "type": "REGULAR",
    "balance": 5000.0
  }
]
```

#### Create Account
**POST** `/database/account/`

**Request Body** (`CreateAccountSchema`):
```json
{
  "name": "Savings Account",
  "type": "SAVINGS", // REGULAR, SAVINGS, CREDIT
  "initial_balance": 1000.0
}
```

**Response** (`AccountSchema`):
```json
{
  "id": 2,
  "name": "Savings Account",
  "type": "SAVINGS",
  "balance": 1000.0
}
```

#### Transfer Funds
**POST** `/database/account/transfer`

**Request Body** (`TransferSchema`):
```json
{
  "from_account_id": 1,
  "to_account_id": 2,
  "amount": 500.0,
  "description": "Saving for later" // Optional
}
```

**Response**:
`"Transfer successful."` (200 OK) or Error Message (400 Bad Request)

### 💸 Income

#### List Income
**GET** `/database/income/?active=true`

**Response** (`IncomeListResponse`):
```json
{
  "status": "success",
  "message": "success",
  "data": [
    {
        "id": 1,
        "user_id": 1,
        "type_income": "Salary",
        "amount": 5000.0,
        "description": "Monthly pay",
        "account_id": null,
        "active": true,
        "icon": "cash-outline",
        "color": "#10b981",
        "created_at": "2025-01-01T12:00:00Z",
        "updated_at": "2025-01-01T12:00:00Z"
    }
  ]
}
```

#### Create Income
**POST** `/database/income/`

**Request Body** (`IncomeCreateSchema`):
```json
{
  "type_income": "Freelance",
  "amount": 2000.0,
  "description": "Project X", // Optional
  "account_id": 1             // Optional: links to account balance
}
```

**Response** (`IncomeResponse`):
```json
{
  "status": "success",
  "message": "Income source created successfully",
  "data": {
      "id": 2,
      "user_id": 1,
      "type_income": "Freelance",
      "amount": 2000.0,
      "description": "Project X",
      "account_id": 1,
      "active": true,
      "icon": "cash-outline",
      "color": "#10b981",
      "created_at": "2025-10-27T10:00:00Z",
      "updated_at": null
  }
}
```

#### Update Income
**PUT** `/database/income/{id}`

**Request Body** (`IncomeUpdateSchema`):
```json
{
  "amount": 2500.0,
  "description": "Updated project description"
}
```

### 💳 Transactions

#### List Transactions
**GET** `/database/transaction/`
Query Params: `active=true`, `start_date=2025-01-01`, `end_date=2025-01-31`, `transaction_type=EXPENSE`, `limit=50`.

**Response** (`TransactionListResponse`):
```json
{
  "status": "success",
  "message": "",
  "data": [
    {
      "id": 1,
      "user_id": 1,
      "date": "2025-10-27",
      "amount": 50.0,
      "time": "09:30:00",
      "description": "Coffee",
      "city": "Cairo",
      "budget_id": 2,
      "neighbourhood": "Maadi",
      "account_id": 1,
      "transfer_to_id": null,
      "transaction_type": "EXPENSE",
      "active": true,
      "created_at": "2025-10-27T09:30:00Z",
      "updated_at": null
    }
  ]
}
```

#### Create Transaction
**POST** `/database/transaction/`

**Request Body** (`TransactionCreateSchema`):
```json
{
  "date": "2025-10-27",
  "amount": 120.50,
  "transaction_type": "EXPENSE", // EXPENSE, INCOME, TRANSFER
  "description": "Grocery run", // Optional
  "budget_id": 2,               // Optional
  "account_id": 1,              // Optional
  "city": "Cairo",              // Optional
  "neighbourhood": "Maadi",     // Optional
  "time": "14:00:00"            // Optional
}
```

#### Update Transaction
**PUT** `/database/transaction/{id}`

**Request Body** (`TransactionUpdateSchema`):
```json
{
  "amount": 130.00,
  "description": "Added milk"
}
```

### 📉 Budgets

#### List Budgets
**GET** `/database/budget/?active=true`

**Response** (`BudgetListResponse`):
```json
{
  "status": "success",
  "message": "",
  "data": [
    {
      "id": 1,
      "budget_name": "Food",
      "description": "Monthly groceries",
      "total_limit": 5000.0,
      "priority_level_int": 1,
      "icon": "wallet",
      "color": "#3162ff",
      "active": true,
      "created_at": "2025-01-01T10:00:00Z",
      "updated_at": "2025-01-01T10:00:00Z"
    }
  ]
}
```

#### Create Budget
**POST** `/database/budget/`

**Request Body** (`BudgetCreateSchema`):
```json
{
    "name": "Entertainment",
    "total_limit": 1000.0,
    "priority_level_int": 2, // Optional
    "description": "Movies and games", // Optional
    "icon": "film",         // Optional
    "color": "#ff0000"      // Optional
}
```

#### Update Budget
**PUT** `/database/budget/{id}`

**Request Body** (`BudgetUpdateSchema`):
```json
{
    "total_limit": 1500.0,
    "name": "Fun & Games"
}
```

### 🎯 Goals

#### List Goals
**GET** `/database/goal/?active=true`

**Response** (`GoalListResponse`):
```json
{
  "status": "success",
  "message": "",
  "data": [
    {
      "id": 1,
      "user_id": 1,
      "goal_name": "Car",
      "description": "Savings for Tesla",
      "target": 50000.0,
      "saved_amount": 10000.0,
      "start_date": "2025-01-01",
      "due_date": "2026-01-01",
      "icon": "car",
      "color": "#ff0000",
      "plan": "Save 1000 monthly",
      "active": true,
      "created_at": "2025-01-01T10:00:00Z",
      "updated_at": null
    }
  ]
}
```

#### Create Goal
**POST** `/database/goal/`

**Request Body** (`GoalCreateSchema`):
```json
{
  "name": "New Phone",
  "target": 20000.0,
  "due_date": "2025-12-31", // Optional
  "plan": "Save 2000 per month", // Optional
  "description": "iPhone 16", // Optional
  "icon": "phone", // Optional
  "color": "#00ff00" // Optional
}
```

#### Update Goal
**PUT** `/database/goal/{id}`

**Request Body** (`GoalUpdateSchema`):
```json
{
  "saved_amount": 5000.0,
  "status": "active" // Optional: "active", "archive", "deleted"
}
```

### 💬 Conversations

#### Start Conversation
**POST** `/database/conversation/start`

**Request Body** (`ConversationStartSchema`):
```json
{
  "channel": "web" // default "web"
}
```

#### Get Messages
**GET** `/database/conversation/{id}/messages`

**Response**:
```json
{
  "status": "success",
  "message": "",
  "data": [
    {
      "id": 101,
      "conversation_id": 1,
      "sender_type": "user", // or "assistant"
      "source_agent": "User",
      "content": "Hello",
      "content_type": "text",
      "created_at": "2025-10-27T10:00:00Z"
    }
  ]
}
```

---

## 📈 Analytics (Advanced)

### Budget Stats
**GET** `/database/analytic/budgets/stats`

**Response** (`BudgetStatsListResponse`):
```json
{
  "status": "success",
  "message": "",
  "data": [
    {
      "id": 1,
      "budget_name": "Food",
      "description": "Monthly groceries",
      "total_limit": 5000.0,
      "priority_level_int": 1,
      "icon": "wallet",
      "color": "#3162ff",
      "active": true,
      "created_at": "2025-01-01T00:00:00Z",
      "updated_at": null,
      "spent": 2500.0,
      "remaining": 2500.0,
      "percentage_used": 50.0,
      "transaction_count": 12
    }
  ]
}
```

### Goal Stats
**GET** `/database/analytic/goals/stats`

**Response** (`GoalStatsListResponse`):
```json
{
    "status": "success",
    "message": "",
    "data": [
        {
            "id": 1,
            "user_id": 1,
            "goal_name": "Car",
            "description": "Tesla Fund",
            "target": 50000.0,
            "saved_amount": 10000.0,
            "start_date": "2025-01-01",
            "due_date": "2026-01-01",
            "icon": "car",
            "color": "#ff0000",
            "plan": "Save aggressively",
            "active": true,
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": null,
            "progress_percentage": 20.0,
            "days_remaining": 200
        }
    ]
}
```

### Transaction Search
**GET** `/database/analytic/transactions/search`
Query Params: `query` (text), `category` (budget name), `min_amount`, `max_amount`, `city`, `neighbourhood`.

**Response**:
```json
{
    "status": "success",
    "data": [
        {
            "id": 1,
            "date": "2025-10-27",
            "amount": 50.0,
            "description": "Coffee match",
            "budget_name": "Food",
            "city": "Cairo",
            "neighbourhood": "Zamalek",
            "account_id": 1,
            "transaction_type": "EXPENSE"
        }
    ],
    "count": 1
}
```

### Monthly Breakdown
**GET** `/database/analytic/monthly-breakdown?month=2025-10-01`

**Response** (`MonthlyBreakdownSchema`):
```json
{
  "total_income": 10000.0,
  "total_spent": 8000.0,
  "net_savings": 2000.0,
  "surplus": true,
  "transaction_count": 45,
  "avg_per_transaction": 177.77,
  "categories": [
    {
      "name": "Food",
      "amount": 3000.0,
      "count": 15,
      "percentage": 37.5,
      "color": "#3162ff",
      "icon": "wallet"
    }
  ]
}
```

