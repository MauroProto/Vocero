# Vocero

## WHAT — Codebase Map

**WhatsApp bot that receives appointment requests (text/voice) and autonomously calls service providers to book appointments using AI voice agents.**

### Tech Stack
- **Backend:** Python 3.12 + FastAPI
- **Database:** PostgreSQL (via Docker)
- **Voice AI:** ElevenLabs Conversational AI + Agentic Functions (tool calling)
- **WhatsApp:** Meta Cloud API (send/receive messages, media download)
- **Telephony:** Twilio (outbound PSTN calls via ElevenLabs integration)
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
│   ├── schemas/
│   │   ├── intent.py        # Intent/entity schemas for NLU
│   │   └── tools.py         # Schemas for voice agent tool webhooks
│   ├── api/
│   │   ├── whatsapp.py      # Meta WhatsApp webhook (GET verify + POST messages)
│   │   ├── callbacks.py     # Twilio call status callbacks
│   │   └── tools.py         # ElevenLabs agent server tool endpoints
│   ├── services/
│   │   ├── twilio.py        # WhatsApp messaging (Meta Cloud API) + media download
│   │   ├── elevenlabs_call.py # Outbound voice calls via ElevenLabs+Twilio
│   │   ├── intent.py        # NLU intent extraction (OpenAI)
│   │   ├── transcription.py # Voice note STT (ElevenLabs Scribe)
│   │   ├── messages.py      # Formatted WhatsApp message templates (EN/ES)
│   │   ├── state.py         # In-memory conversation state machine
│   │   └── contact.py       # Contact/vCard parsing
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
1. User sends WhatsApp message or voice note (received via Meta Cloud API webhook).
2. Voice note transcribed (ElevenLabs Scribe); text parsed for intent (OpenAI GPT-4.1-mini).
3. User shares provider contact or phone number.
4. Vocero places outbound call via ElevenLabs voice agent (uses Twilio for PSTN).
5. AI agent negotiates appointment slots, calling server tools (`/api/tools/*`) mid-conversation.
6. Real-time WhatsApp updates: "Calling...", "Has availability!", "Booking confirmed!".
7. Results sent back as structured WhatsApp message. Transcript emailable via Resend.

**Domain Rules:**
- One user can have multiple active appointment requests.
- Each outbound call is tracked with status, transcript, and outcome.
- The voice agent uses server tools (webhooks) to report slots, confirm bookings, and escalate to user.

## HOW — Working Rules

### Build & Run
```bash
docker compose up --build        # Start Postgres + app
docker compose up -d db          # Postgres only
uvicorn app.main:app --reload    # Dev server (works without DB too)
ngrok http 8000                  # Expose for Meta webhook
```

### Environment
- Copy `.env.example` → `.env` and fill in API keys.
- Set ngrok URL as webhook in Meta Developers → WhatsApp → Configuration.
- Webhook verify token: `vocero_verify`
- Subscribe to `messages` field in Meta webhook config.

### Key API Routes
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/whatsapp` | Meta webhook verification (hub.challenge) |
| POST | `/api/whatsapp` | Incoming WhatsApp messages from Meta |
| POST | `/api/call-status` | Twilio call status callbacks |
| POST | `/api/tools/report_available_slots` | Agent reports provider slots |
| POST | `/api/tools/check_user_preference` | Agent validates slot vs user prefs |
| POST | `/api/tools/confirm_booking` | Agent confirms booking → WhatsApp notification |
| POST | `/api/tools/end_call_no_availability` | Agent reports no availability |
| GET | `/health` | Health check |

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
- For more information on how and when to use them refer to /agent-teams-guide.md

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
- [`docs/integrations/twilio.md`](docs/integrations/twilio.md) — Outbound PSTN calls, call status callbacks.
- [`docs/integrations/meta_whatsapp.md`](docs/integrations/meta_whatsapp.md) — Meta Cloud API webhook, sending messages, media download.
- [`docs/integrations/resend.md`](docs/integrations/resend.md) — Email transcript delivery.
- [`docs/strategy.md`](docs/strategy.md) — Hackathon strategy, differentiators, demo script, risk mitigation.
- [`VOCERO_Plan_Integral.md`](VOCERO_Plan_Integral.md) — Full project plan (Spanish): NLU intents, conversation state, agentic functions detail, timeline.
