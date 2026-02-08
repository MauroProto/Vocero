<div align="center">

# VOCERO

**Your AI assistant that makes phone calls so you don't have to.**

Send a WhatsApp message. Vocero calls the provider, books the appointment, and reports back.

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![ElevenLabs](https://img.shields.io/badge/ElevenLabs-Agents-000000?logo=data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjQiIGhlaWdodD0iMjQiPjxyZWN0IHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgZmlsbD0iIzAwMCIvPjwvc3ZnPg==)](https://elevenlabs.io)
[![Twilio](https://img.shields.io/badge/Twilio-Voice-F22F46?logo=twilio&logoColor=white)](https://twilio.com)

</div>

---

## How it works

```
 WhatsApp                    Vocero                     Provider
 ─────────                  ────────                   ──────────
    │                          │                           │
    │  "Book me a haircut      │                           │
    │   for tomorrow at 10"    │                           │
    │ ─────────────────────▶   │                           │
    │                          │   ☎️ AI voice call         │
    │                          │ ─────────────────────▶    │
    │                          │                           │
    │                          │   "Hi, I'm calling on     │
    │                          │    behalf of Mauro..."     │
    │                          │                           │
    │  "Calling provider..."   │   ◀─────────────────────  │
    │ ◀─────────────────────   │   "Thursday 10am works"   │
    │                          │                           │
    │  "Booked! Thu at 10am"   │                           │
    │  "Add to calendar: 🔗"   │                           │
    │ ◀─────────────────────   │                           │
```

**Two-agent architecture:**

1. **WhatsApp Agent** — FastAPI backend that receives messages, understands intent, orchestrates calls, and delivers results
2. **Phone Agent** — ElevenLabs voice AI that actually speaks on the phone, negotiates appointments, and uses mid-call tools

## Features

- **Voice & text input** — Send text messages or voice notes in English or Spanish
- **Smart intent parsing** — NLU extracts what you need, who to call, and when
- **AI phone calls** — ElevenLabs voice agent calls providers and negotiates in natural language
- **Google Places search** — "Find me a dentist in Palermo" → ranked results with ratings
- **Parallel calls** — Call up to 3 providers simultaneously, get ranked results
- **Real-time updates** — WhatsApp progress messages as the call happens
- **Calendar integration** — Google Calendar link sent after confirmed bookings
- **Bilingual** — Full EN/ES support across all messages and voice calls

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12 + FastAPI |
| Database | PostgreSQL 16 (Docker) |
| Voice AI | ElevenLabs Conversational AI |
| Telephony | Twilio (outbound PSTN) |
| WhatsApp | Meta Cloud API |
| NLU | OpenAI GPT |
| Search | Google Places API (New) |
| Email | Resend |

## Project Structure

```
vocero/
├── app/
│   ├── main.py                  # FastAPI entry + routers
│   ├── config.py                # Pydantic Settings
│   ├── api/
│   │   ├── whatsapp.py          # Meta webhook (incoming messages)
│   │   ├── callbacks.py         # Twilio call status + post-call processing
│   │   └── tools.py             # ElevenLabs server tools (mid-call webhooks)
│   ├── services/
│   │   ├── elevenlabs_call.py   # Outbound calls via register-call + Twilio
│   │   ├── intent.py            # NLU intent extraction (OpenAI)
│   │   ├── transcription.py     # Voice note STT (ElevenLabs Scribe)
│   │   ├── messages.py          # WhatsApp message templates + GPT summaries
│   │   ├── calendar.py          # Google Calendar link generator
│   │   ├── places.py            # Google Places search
│   │   ├── state.py             # In-memory conversation state machine
│   │   ├── ranking.py           # Multi-call result ranking
│   │   └── twilio.py            # WhatsApp messaging via Meta Cloud API
│   └── schemas/
│       ├── intent.py            # Intent/entity schemas
│       └── tools.py             # Voice agent tool schemas
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env.example
```

## Quick Start

### Prerequisites

- Python 3.12+
- Docker & Docker Compose
- [ngrok](https://ngrok.com) (to expose local server for webhooks)
- API keys: Twilio, ElevenLabs, Meta WhatsApp, OpenAI, Google Places

### 1. Clone & configure

```bash
git clone https://github.com/your-username/vocero.git
cd vocero
cp .env.example .env
# Fill in your API keys in .env
```

### 2. Run

**With Docker:**
```bash
docker compose up --build
```

**Without Docker (dev):**
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 3. Expose & connect

```bash
ngrok http 8000
```

Set the ngrok URL as your webhook in:
- **Meta Developers** → WhatsApp → Configuration → `{ngrok_url}/api/whatsapp`
- **Twilio Console** → Phone Number → `{ngrok_url}/api/call-status`
- **ElevenLabs** → Agent → Server tools → `{ngrok_url}/api/tools/*`

### Environment Variables

```env
# Twilio
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_PHONE_NUMBER=+1234567890

# Meta WhatsApp Cloud API
META_PHONE_NUMBER_ID=
META_WABA_ID=
META_ACCESS_TOKEN=
META_WEBHOOK_VERIFY_TOKEN=vocero_verify

# ElevenLabs
ELEVENLABS_API_KEY=
ELEVENLABS_AGENT_ID=
ELEVENLABS_AGENT_ID_EN=          # English voice agent (optional)
ELEVENLABS_PHONE_NUMBER_ID=

# OpenAI
OPENAI_API_KEY=

# Google Places
GOOGLE_PLACES_API_KEY=

# App
APP_BASE_URL=https://your-ngrok-url.dev
DEBUG=true
```

## API Routes

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/whatsapp` | Meta webhook verification |
| `POST` | `/api/whatsapp` | Incoming WhatsApp messages |
| `POST` | `/api/call-status` | Twilio call status callbacks |
| `POST` | `/api/tools/report_available_slots` | Agent reports provider availability |
| `POST` | `/api/tools/check_user_preference` | Agent validates slot vs user preference |
| `POST` | `/api/tools/confirm_booking` | Agent confirms a booking |
| `POST` | `/api/tools/end_call_no_availability` | Agent reports no availability |
| `GET` | `/health` | Health check |

## How Outbound Calls Work

Vocero uses ElevenLabs' native Twilio integration — no manual audio bridging:

1. Backend calls `POST /v1/convai/twilio/register-call` with agent config + dynamic variables
2. ElevenLabs returns TwiML with `<Connect><Stream>` pointing to their WebSocket
3. Twilio creates the call using that TwiML
4. **Twilio connects directly to ElevenLabs** — audio format handled natively
5. Mid-call, the voice agent triggers server tools (webhooks) to report slots, confirm bookings, etc.
6. On call completion, GPT analyzes the full transcript and sends a structured summary to WhatsApp

## License

MIT

---

<div align="center">

Built for the **ElevenLabs CallPilot Challenge**

</div>
