# Architecture Overview

## System Diagram

```
User (WhatsApp)
    │
    ▼
Twilio WhatsApp API ──webhook──▶ FastAPI (Vocero Backend)
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                  ▼
              Intent Parser    Voice Note          DB (Postgres)
              (LLM-based)     Transcription        ┌──────────┐
                    │               │               │ Users    │
                    ▼               ▼               │ Requests │
              Appointment Orchestrator              │ CallLogs │
                    │                               │ Appts    │
                    ▼                               └──────────┘
            ElevenLabs Voice Agent
                    │
                    ▼
            Twilio Outbound Call ──────▶ Service Provider (phone)
                    │
                    ▼
            Call Result + Transcript
                    │
            ┌───────┴───────┐
            ▼               ▼
    WhatsApp Response   Resend Email
    (structured msg)    (transcript)
```

## Components

### API Layer (`app/api/`)
- **WhatsApp webhook** — Receives Twilio webhooks for incoming messages and voice notes.
- **Callbacks** — Handles Twilio call status updates and ElevenLabs agent events.

### Service Layer (`app/services/`)
- **WhatsApp service** — Parses incoming messages, formats outgoing responses, sends via Twilio API.
- **Transcription service** — Downloads voice note audio, transcribes to text.
- **Intent service** — Uses LLM to extract structured appointment intent from natural language.
- **Caller service** — Orchestrates ElevenLabs voice agent + Twilio outbound calls.
- **Appointment service** — Manages the full booking lifecycle, coordinates multi-provider calls.
- **Email service** — Sends transcripts via Resend.

### Data Layer (`app/models/`, `app/db/`)
- SQLAlchemy ORM models mapped to PostgreSQL.
- Async session management via `asyncpg`.

### External Services
| Service | Purpose |
|---------|---------|
| Twilio | WhatsApp messaging + outbound phone calls |
| ElevenLabs | Conversational AI voice agent |
| Resend | Email delivery for transcripts |
| LLM (TBD) | Intent parsing from user messages |

## Boundaries
- **API layer** handles HTTP/webhook concerns only. No business logic.
- **Service layer** contains all business logic. Services call each other, never models directly from API.
- **Data layer** is accessed only through services, never directly from routes.
