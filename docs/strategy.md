# Vocero — Hackathon Strategy

## Competitive Positioning

**Narrative:** "Every other team built a web app. We built something 2 billion people can use today without downloading anything."

### Table Stakes (every team builds this)
- Web UI with text input
- Single voice agent calls one provider
- Basic tool calling

### Our Differentiators (ranked by impact)
1. **WhatsApp-first UX** — No app, no web UI. Judges see this and remember it.
2. **Escalate-to-user mid-call** — Agent sends WhatsApp message DURING the call asking user to choose between slots. Jaw-dropping demo moment.
3. **Real-time progress narration** — WhatsApp messages stream as calls happen.
4. **Voice note input** — Full speech-to-speech pipeline.
5. **Multilingual** — Auto-detect language from user message, agent speaks English or Spanish.
6. **Parallel multi-provider calls** — Call 3+ providers, rank results.

## Architecture (Final)

### Two-Agent Design
1. **WhatsApp Agent** = Our FastAPI backend
   - Receives user messages via Twilio WhatsApp Sandbox webhook
   - Transcribes voice notes (OpenAI Whisper or ElevenLabs STT)
   - Parses intent using LLM
   - Orchestrates outbound calls via ElevenLabs API
   - Sends progress updates + structured results back via Twilio REST API
   - Handles mid-call escalation (receives user replies, relays to phone agent)

2. **Phone Agent** = ElevenLabs Conversational AI voice agent
   - Calls providers via Twilio PSTN (native integration)
   - Negotiates appointments in natural conversation
   - Uses server tools (webhooks to our FastAPI) to report slots, confirm bookings
   - Supports EN + ES via dynamic variables

### Data Flow
```
User (WhatsApp) → Twilio Sandbox → FastAPI webhook → intent parsing →
  → ElevenLabs outbound call API → Phone Agent calls provider →
  → Agent uses server tools (webhooks) → FastAPI stores results →
  → FastAPI sends WhatsApp response via Twilio REST API → User
```

### Architecture Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| WhatsApp interface | Twilio Sandbox | No Meta Business Manager needed. Fast setup for hackathon. |
| Outbound calls | ElevenLabs native Twilio integration | One API call = one outbound call. No WebSocket plumbing. |
| Agent design | Two agents (WhatsApp + Phone) | Separation of concerns. Each agent has focused role. |
| Demo providers | Teammate plays receptionist | Natural, unpredictable, shows real handling. |
| Mid-call escalation | Must-have | Highest-impact differentiator. |
| Language | Multilingual (EN + ES) | Matches "Vocero" branding. |
| UI | WhatsApp only | No web UI. Forces the narrative. |

## Demo Script (outline)

1. Open WhatsApp, send voice note in Spanish: "Necesito una cita con el dentista esta semana por la tarde"
2. Bot transcribes, confirms intent in Spanish
3. Bot starts calling 2-3 providers, sends real-time updates
4. Mid-call: agent finds two slots, sends WhatsApp asking user to pick
5. User replies "la primera"
6. Agent confirms booking, sends structured WhatsApp with details
7. User requests transcript → receives email

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| ElevenLabs outbound calls don't work | Test single call FIRST, before anything else |
| Tool call latency >500ms | Keep tool handlers simple, in-memory data |
| WhatsApp sandbox limitations | Pre-register demo phone numbers |
| Multilingual voice quality | Test Spanish voices early, fallback to English |
| Mid-call escalation timing | Agent holds conversation while waiting for user reply |

## What We Skip
- Web UI / dashboard
- User authentication / accounts
- Payment integration
- Real provider database (use mock data)
- CI/CD, production infra
- Persistent conversation history across sessions
- Google Calendar integration (simulate availability)
- ElevenLabs native WhatsApp (requires Meta Business Manager)
