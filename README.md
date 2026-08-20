# ShopSense

ShopSense is an AI-assisted e-commerce support workflow. It triages tickets, retrieves grounded policy answers, performs safe order actions, and routes high-risk cases to human approval. The project includes a FastAPI API and a Vite/React dashboard.

## Features

- Ticket triage extracts issue type, order ID, sentiment, urgency, and suspected prompt-injection attempts.
- Policy questions use hybrid retrieval and a groundedness check before an answer is returned with its policy sources.
- Refund, return, and order-status workflows use mock order-system tools and enforce refund guardrails.
- Higher-risk tickets pause for approve/reject review; state is persisted so they can be resumed later.
- The dashboard shows ticket history, workflow status, policy answers, source tags, and human-review warnings.
- A FastMCP server makes order lookup, shipment status, refund calculation, and refund/replacement actions available as reusable MCP tools.

## Stack

- **Backend:** Python, FastAPI, and Pydantic provide typed HTTP endpoints and request/response validation.
- **Agent workflow:** LangGraph models the stateful triage → retrieval/action → escalation → resolution flow, with SQLite checkpoints for resumable approval tasks.
- **AI and retrieval:** LiteLLM connects to the configured model provider; Qdrant combines dense semantic search and BM25-style keyword retrieval over the policy handbook, followed by reranking and groundedness checks.
- **Business tools and safety:** Mock order-system tools simulate lookups and refund actions; retries, circuit breakers, refund guardrails, and prompt-injection detection keep actions controlled.
- **Tool integration:** FastMCP exposes those order capabilities through a standard Model Context Protocol (MCP) tool server for agent or client integration.
- **Frontend:** React, TypeScript, Vite, TanStack Query, and Tailwind CSS power the dashboard and API state management.
- **Quality and observability:** Pytest covers the backend and golden evaluations; optional Langfuse tracing captures ticket-level workflow and node activity.

## How it works

LangGraph coordinates the workflow: triage routes policy questions to RAG and order requests to the order tools, then an escalation check either resolves the ticket or pauses it for a human decision. SQLite stores checkpoints and customer memory; Qdrant stores the local policy index. Optional Langfuse tracing records workflow activity without affecting ticket processing.

## Project structure

- `src/` — API, LangGraph workflow, agents, MCP server, retrieval, and guardrails
- `frontend/` — React dashboard
- `tests/` — unit, API, reliability, and golden-evaluation tests
- `data/` — policy handbook, mock orders, and evaluation tickets

## Key design decisions

- **Human-in-the-loop:** high-risk or ambiguous requests pause instead of executing automatically.
- **Grounded RAG:** answers include retrieved policy sources and are checked for unsupported claims.
- **Safe integrations:** retries and circuit breakers turn order-system failures into escalation, not silent failures.

## Quick start

Use Python 3.11+ and Node.js 20+.

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn src.main:app --reload
```

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open the dashboard URL printed by Vite (normally `http://127.0.0.1:5173`). The API runs at `http://127.0.0.1:8000`; its interactive documentation is at `/docs`.

## Configuration

Create a local `.env` file for configuration. `MOCK_LLM=true` uses deterministic mock triage. For live LLM-backed flows, set `MOCK_LLM=false`, configure `LLM_MODEL`, and provide the matching provider credential (for example, `GEMINI_API_KEY`). Langfuse variables are optional and enable tracing.

The frontend defaults to `http://127.0.0.1:8000`. To use another API URL, copy `frontend/.env.example` to `frontend/.env` and update `VITE_API_BASE_URL`.

## API workflow

- `POST /tickets` creates and processes a ticket.
- `GET /tickets/{thread_id}` retrieves its latest state.
- `POST /tickets/{thread_id}/resume` approves or rejects a paused ticket.

Low-risk tickets complete automatically. Tickets involving high refunds, urgent/angry sentiment, suspected prompt injection, or unsafe policy output pause for human review.

## Verification

```powershell
python -m pytest tests -v
python -m scripts.run_golden_eval

cd frontend
npm run build
```
