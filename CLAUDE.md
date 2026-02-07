# Vocero

## WHAT — Codebase Map

**WhatsApp bot that receives appointment requests (text/voice) and autonomously calls service providers to book appointments using AI voice agents.**

### Tech Stack
- **Backend:** Python 3.12 + FastAPI
- **Database:** PostgreSQL (via Docker)
- **Voice AI:** ElevenLabs Conversational AI + Agentic Functions (tool calling)
- **Telephony + WhatsApp:** Twilio (WhatsApp Sandbox + outbound PSTN calls)
- **Email:** Resend (call transcript delivery)
- **Deps:** pip + requirements.txt

### Two-Agent Architecture
1. **WhatsApp Agent** = Our FastAPI backend — receives messages, parses intent, orchestrates calls, sends results
2. **Phone Agent** = ElevenLabs voice agent — calls providers via Twilio, negotiates appointments, uses server tools

### Repo Structure
```
Vocero/
├── app/
│   ├── main.py              # FastAPI entry, lifespan, routers
│   ├── config.py            # Pydantic Settings (all env vars)
│   ├── models/              # SQLAlchemy ORM models
│   ├── schemas/             # Pydantic request/response schemas
│   ├── api/                 # Route handlers (whatsapp webhook, callbacks, tools)
│   ├── services/            # Business logic (caller, intent, transcription, email)
│   └── db/                  # Database engine + session management
├── docs/                    # Progressive-disclosure documentation
├── features.json            # Machine-readable feature tracking
├── progress.md              # Human-readable progress log
├── docker-compose.yml       # Postgres + app containers
├── Dockerfile
└── requirements.txt
```

## WHY — Domain & Purpose

**Users:** People who need to book appointments (doctor, hairdresser, mechanic) but don't want to call around.

**Core Flow:**
1. User sends WhatsApp message or voice note describing what they need.
2. Voice note is transcribed; text is parsed for intent (service type, time, location).
3. Vocero places outbound calls to providers using ElevenLabs voice agents via Twilio.
4. AI agent negotiates appointment slots in natural conversation.
5. Mid-call: agent can escalate to user via WhatsApp for decisions (key differentiator).
6. Results sent back as structured WhatsApp message. Transcript emailable via Resend.

**Domain Rules:**
- One user can have multiple active appointment requests.
- Each outbound call is tracked with status, transcript, and outcome.
- The voice agent uses server tools (webhooks) to report slots, confirm bookings, and escalate to user.

## HOW — Working Rules

### Build & Run
```bash
docker compose up --build        # Start Postgres + app
docker compose up -d db          # Postgres only
uvicorn app.main:app --reload    # Dev server (needs Postgres running)
ngrok http 8000                  # Expose for Twilio webhooks
```

### Environment
- Copy `.env.example` → `.env` and fill in API keys.
- Set ngrok public URL in Twilio console for WhatsApp webhook.

### Working Principles

**Architecture & Code Quality:**
- Clean architecture. SOLID principles. Don't overengineer.
- Services layer owns business logic. Routes are thin.
- Async everywhere (routes, services, db).
- No unnecessary defensive code — skip try/catch in trusted internal codepaths.
- No `print()` — use `logging`. Remove debug logs before committing.
- Keep code readable. Three similar lines > premature abstraction.

**Development Flow:**
- Small, reversible changes. One feature at a time.
- Respect existing patterns unless there's a clear bug.
- Ask for clarification on ambiguous or conflicting requirements.
- Plan first for non-trivial tasks (3+ steps or architectural decisions).
- If something goes sideways, STOP and re-plan — don't keep pushing.

**Verification:**
- Never mark a task complete without proving it works.
- Run the test commands specified in `features.json` for each feature.
- Ask yourself: "Would a staff engineer approve this?"

**Autonomy & Bug Fixing:**
- When given a bug: just fix it. Point at logs, errors — then resolve.
- Zero context switching required from the user.
- Go fix failing issues without being told how.

**Simplicity First:**
- Make every change as simple as possible. Impact minimal code.
- No temporary fixes. Find root causes.
- Changes should only touch what's necessary.

### Parallelism Strategy
- **Subagents** (default): Independent focused tasks where only the result matters — codebase exploration, file-scoped edits, research. Results return to main. Low overhead.
- **Decision rule**: If tasks are independent and results just flow back → subagents. Use subagents liberally to keep main context window clean. One task per subagent for focused execution.

### Task Tracking
When implementing features from `features.json`, always create tasks to track progress (`TaskCreate`, `TaskGet`, `TaskUpdate`). After completing a feature:
1. Update `features.json` status to `true`.
2. Append entry to `progress.md`.
3. Commit with format: `feat: <feature_id> – <description>`.

### Self-Improvement Loop
- After ANY correction from the user: update memory with the pattern.
- Write rules that prevent the same mistake.
- Review lessons at session start.

### Commit Format
- `feat: <feature_id> – <short description>`
- `fix: <feature_id> – <short description>`
- `chore: <short description>`

### Stateless Recovery
If session dies or context resets, recover by reading:
1. This `CLAUDE.md`
2. `features.json` (what's done, what's next)
3. `progress.md` (what happened)
4. `git log --oneline` (recent commits)

## Further Docs

> Only read these when the current task needs them (progressive disclosure).

- [`docs/architecture/overview.md`](docs/architecture/overview.md) — System architecture, component diagram, API boundaries.
- [`docs/conventions/code_conventions.md`](docs/conventions/code_conventions.md) — Error handling, logging, async, naming patterns.
- [`docs/domain/domain_overview.md`](docs/domain/domain_overview.md) — Core entities, relationships, user journeys.
- [`docs/integrations/elevenlabs.md`](docs/integrations/elevenlabs.md) — ElevenLabs agent setup, outbound calls, server tools, transcripts.
- [`docs/integrations/twilio.md`](docs/integrations/twilio.md) — WhatsApp webhook, voice notes, outbound calls, parallel calls.
- [`docs/integrations/resend.md`](docs/integrations/resend.md) — Email transcript delivery.
- [`docs/strategy.md`](docs/strategy.md) — Hackathon strategy, differentiators, demo script, risk mitigation.
- [`VOCERO_Plan_Integral.md`](VOCERO_Plan_Integral.md) — Full project plan (Spanish): NLU intents, conversation state, agentic functions detail, timeline.
