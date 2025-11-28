---
title: Financial Guardian AI
emoji: 🛡️💰
colorFrom: green
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
license: mit
short_description: AI Financial Advisor with LangGraph Multi-Agent System
tags:
- finance
- chatbot
- langgraph
- multi-agent
- rag
- fastapi
- pinecone
- groq
---

# Financial Guardian AI 🛡️💰

An AI-powered financial advisor and planner built with **LangGraph multi-agent orchestration**. Features intelligent financial analysis, budget tracking, goal management, and RAG-powered knowledge retrieval.

## 🏗️ Architecture

```
User Query → Supervisor Agent → Specialist Agents → Response
                    │
        ┌───────────┼───────────┐
        │           │           │
   Analyst    Planner    Transaction    Knowledge
   Agent      Agent        Agent         Agent
```

### Agent System

| Agent | Model | Role |
|-------|-------|------|
| **Supervisor** | gpt-oss-20b | Routes queries to appropriate specialists |
| **Analyst** | llama-4-scout | Spending analysis, anomaly detection, forecasting |
| **Planner** | gpt-oss-20b | Budgets, goals, financial planning |
| **Transaction** | llama-4-maverick | Expense logging, manual transactions |
| **Knowledge** | llama-4-scout | RAG-based financial literacy & RBI guidelines |

## 🚀 Features

- **Multi-Agent Orchestration**: LangGraph-powered intelligent routing
- **Financial Analysis**: Spending patterns, category breakdowns, trend analysis
- **Budget Management**: Set, track, and manage category budgets
- **Goal Tracking**: Savings goals with progress monitoring
- **RAG Pipeline**: Pinecone-powered financial knowledge retrieval
- **Dual-Action Support**: Handle complex queries (e.g., "spent 500 on food, update food savings goal")
- **Liability Tracking**: Loans and credit card management

## 📡 API Endpoints

### Chat
- `POST /api/chat/message` - Main chat endpoint (Supervisor → Agents)

### Budgets
- `GET /api/budgets` - Get budget status
- `POST /api/budgets` - Create/update budget
- `DELETE /api/budgets/{category}` - Delete budget

### Goals
- `GET /api/goals` - Get all goals
- `POST /api/goals` - Create goal
- `PUT /api/goals/{goal_id}` - Update goal progress
- `DELETE /api/goals/{goal_id}` - Delete goal

### Transactions
- `POST /api/transactions/manual` - Add manual transaction
- `GET /api/transactions/manual` - Get manual transactions
- `GET /api/transactions` - Get all transactions

### Dashboard
- `GET /api/snapshot` - Full financial snapshot
- `GET /api/liabilities` - Loans & credit cards

### Data
- `POST /api/data/sync-setu` - Sync bank data via Setu API
- `POST /api/data/freshness` - Check data freshness

### Health
- `GET /health` - Service health check
- `GET /docs` - Interactive API documentation

## ⚙️ Environment Variables

Configure these in your Hugging Face Space settings:

| Variable | Description | Required |
|----------|-------------|----------|
| `GROQ_API_KEY` | Groq LLM API key | ✅ |
| `PINECONE_API_KEY` | Pinecone vector database API key | ✅ |
| `PINECONE_INDEX` | Pinecone index name (default: `financial-guardian-rag`) | ❌ |

## 🧪 Local Development

```bash
# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows
source venv/bin/activate      # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your API keys

# Seed database
python -m scripts.seed_database

# Run server
uvicorn app.main:app --reload --port 5001
```

## 🐳 Docker

```bash
# Build image
docker build -t financial-guardian .

# Run container
docker run -p 7860:7860 \
  -e GROQ_API_KEY=your_key \
  -e PINECONE_API_KEY=your_key \
  financial-guardian
```

## 📊 Tech Stack

- **Framework**: FastAPI
- **Orchestration**: LangGraph
- **LLMs**: Groq (llama-4-scout, llama-4-maverick, gpt-oss-20b)
- **Vector DB**: Pinecone
- **Database**: SQLite
- **Embeddings**: multilingual-e5-large

## 📝 Example Queries

```
"How much did I spend on food this month?"
"Set a budget of 5000 for shopping"
"Create a goal to save 50000 for vacation by March"
"I spent 300 on groceries today"
"What are the tax saving options under 80C?"
"Spent 500 on food, also update my food savings goal"
```

---

Built with ❤️ for Mumbai Hacks 2025
