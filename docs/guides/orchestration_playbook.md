# Orchestration Playbook: Serving “Any Company” Requests

This note describes three complementary patterns you can adopt to let the chatbot pull fresh financial data on demand. They correspond to the suggestions we discussed:

1. **Local Queue/Worker Layer (Option A)** – Add a small job manager inside the project so requests are queued, rate-limited, retried, and cached before the chatbot reads the results.
2. **Hosted / Serverless Fetchers (Option B)** – Push the heavy lifting to managed services (AWS Lambda, Azure Functions, GCP Cloud Run, etc.) that orchestrate data pulls at scale.
3. **Ad-hoc Batch Script (Option C)** – Run a simple Python script to refresh a curated list of tickers in one shot (ideal for nightly “coverage lists”).

Each section below explains the architecture, the moving parts, and how to integrate with the existing `BenchmarkOSChatbot` codebase.

---

## Option A – Local Queue/Worker Layer

### Overview
- Introduce a lightweight task queue (`TaskManager`) that accepts “ingest ticker” jobs.
- Workers run inside the same process (ThreadPool/async) or a helper daemon.
- Enforce rate limiting + retries so that data sources (Yahoo/SEC) are not hammered.
- Cache results (SQLite tables we already have) and notify the chatbot when ready.

### Components
1. **`tasks.py`** (new) – central queue, background executor, and retry policies.
2. **Ingestion** – enqueue jobs instead of fetching immediately in the chatbot.
3. **Analytics** – the `AnalyticsEngine` checks the queue/cache, waits or polls.
4. **Status API** – optional channel so the chatbot reports "Fetching…" vs. "Ready".

### Flow
1. User asks for `metrics for MSFT phase 1`.
2. `AnalyticsEngine.get_metrics` sees data missing and calls `TaskManager.submit_ingest("MSFT", years=5)`.
3. Worker runs `ingest_live_tickers`, respecting the configured delay between API calls.
4. When done, it refreshes metrics (same as we do now) and marks the job `completed`.
5. Chatbot polls the job status; once complete, it re-runs `get_metrics` and responds with numbers.

### Implementation Tips
- Start with an in-process executor (see `src/benchmarkos_chatabot/tasks.py`).
- Configure rate limits via a simple `asyncio.Semaphore` or `time.sleep` between jobs (e.g., no more than 1 job / 2 seconds).
- Add `TaskStatus` enumeration (`pending`, `running`, `succeeded`, `failed`).
- Persist job history in SQLite (`jobs` table) for traceability.
- For concurrency beyond a single machine, plug in Redis + RQ, Celery, Dramatiq, or Airflow.

### Files to Review
- `src/benchmarkos_chatbot/tasks.py` – starter queue implementation.
- `src/benchmarkos_chatbot/chatbot.py` – you can swap the direct ingest call with `TaskManager.submit_ingest`.
- `src/benchmarkos_chatbot/analytics_engine.py` – add polling logic that checks job completion before returning a final answer.

---

## Option B – Hosted / Serverless Fetchers

### Overview
Use managed services to execute fetch/normalise jobs outside your runtime. Helpful if:
- You need to ingest large batches (hundreds of tickers).
- You want horizontal scaling without managing servers.

### Suggested Architecture
1. **Chatbot** – still detects missing tickers.
2. **Message Broker** – e.g., AWS SQS, Azure Service Bus, Google Pub/Sub.
3. **Serverless Worker** – Lambda/Function/Cloud Run triggered by the queue. It reads jobs, calls APIs, writes into your storage (S3, DynamoDB, Azure Table, Postgres, etc.).
4. **Storage** – keep both raw JSON (for auditing) and normalised facts (similar to `FinancialFact`).
5. **Notification** – after ingestion the worker publishes a message (SQS/SNS/EventBridge) or sets a flag in storage.
6. **Chatbot Polling** – polls storage or listens to WebSocket/push notifications to know when data is ready.

### Advantages
- Scale automatically with demand.
- Separation between chat and ingestion logic.
- Easier to meet compliance guidelines (infrastructure-as-code, IAM policies).

### Implementation Steps
1. Package the `ingest_live_tickers` logic into a function that takes `ticker`, `years`, and storage credentials.
2. Create a lightweight Lambda/Function that wraps this function.
3. Expose an HTTPS endpoint or queue trigger; from the chatbot, POST the job request.
4. Use a database/queue to track job status and TTLs.
5. Update the chatbot to poll for job completion (or display "Your data is being prepared, check back soon").

> **Note:** Hosting costs, limits, and security policies apply—plan around API keys, per-seat licensing, and the provider’s SLA.

---

## Option C – Ad-hoc Batch Script

### Overview
For teams that prefer daily/weekly refreshes, a simple script can ingest a curated list of tickers in one run. This is a pragmatic option when you don’t need real-time updates but want broad coverage preloaded in SQLite.

### How to Use
1. Edit `batch_ingest.py` and update `TICKERS` with your coverage list.
2. Run `py -3 batch_ingest.py` in the project root (run inside a virtual environment if you use one).
3. The script ingests each ticker sequentially, refreshing KPIs as it goes.
4. After the script finishes, the chatbot already has the data; `list companies` will include everything you loaded.

### Scheduling
- Windows Task Scheduler, cron, or GitHub Actions can run `batch_ingest.py` nightly.
- Log output to a file so you can inspect failures.

---

## Where to Look Next
- `docs/` – you can expand this playbook with your own runbooks.
- `batch_ingest.py` – the ad-hoc batch example.
- `src/benchmarkos_chatbot/tasks.py` – scaffolding for the local queue.
- `README.md` – updated instructions on setting API user-agent and running the scripts.

Feel free to adjust these patterns to match your data licensing and infrastructure. Combine them if you like: e.g., a daily batch for high-priority tickers plus on-demand jobs for long-tail symbols.
