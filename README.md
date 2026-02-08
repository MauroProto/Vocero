<div align="center">

<br>

# `VOCERO`

**Your AI assistant that makes phone calls so you don't have to.**

Send a WhatsApp message. Vocero calls the provider, books your appointment, and reports back.

<br>

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/fastapi-0.115-00897B?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![ElevenLabs](https://img.shields.io/badge/elevenlabs-agents-5D3FD3?style=flat-square)](https://elevenlabs.io)
[![Twilio](https://img.shields.io/badge/twilio-voice-E8381E?style=flat-square&logo=twilio&logoColor=white)](https://twilio.com)
[![OpenAI](https://img.shields.io/badge/openai-GPT-412991?style=flat-square&logo=openai&logoColor=white)](https://openai.com)

<br>

</div>

## Overview

Vocero is a **two-agent system** that automates appointment booking through WhatsApp:

> **You** text WhatsApp or send a voice note &rarr; **WhatsApp Agent** understands your request &rarr; **Phone Agent** calls the provider &rarr; books the appointment &rarr; sends you the result + calendar link

| WhatsApp Agent | Phone Agent |
|---|---|
| FastAPI backend | ElevenLabs voice AI |
| Receives messages, parses intent | Speaks on the phone in real time |
| Orchestrates calls, delivers results | Negotiates appointments, uses mid-call tools |

<br>

## Features

| | Feature | Description |
|---|---|---|
| **Voice & Text** | Send text or voice notes | Automatic transcription via ElevenLabs Scribe |
| **Smart NLU** | Intent extraction | GPT parses what you need, who to call, when |
| **AI Calls** | Autonomous phone calls | Voice agent negotiates with providers naturally |
| **Search** | Google Places | "Find a dentist near me" &rarr; ranked results |
| **Parallel** | Multi-provider calls | Call multiple providers simultaneously |
| **Live Updates** | Real-time progress | WhatsApp messages as the call happens |
| **Calendar** | Auto calendar link | Google Calendar event after confirmed bookings |
| **Multilingual** | Multilingual by design | Full support across voice, messages, and UI |

<br>

## Tech Stack

```
WhatsApp (Meta Cloud API)
    ↓
FastAPI + Python 3.12          ←→  OpenAI GPT (NLU + summaries)
    ↓                          ←→  Google Places API (search)
ElevenLabs Conversational AI   ←→  Twilio (PSTN calls)
    ↓
PostgreSQL (Docker)
```

<br>

## Project Structure

```
app/
├── main.py                    # Entry point + routers
├── config.py                  # Pydantic Settings (env vars)
├── api/
│   ├── whatsapp.py            # Meta webhook — incoming messages
│   ├── callbacks.py           # Twilio status + post-call processing
│   └── tools.py               # ElevenLabs mid-call server tools
├── services/
│   ├── elevenlabs_call.py     # Outbound calls (register-call + Twilio)
│   ├── intent.py              # NLU intent extraction
│   ├── transcription.py       # Voice note STT
│   ├── messages.py            # Message templates + GPT summaries
│   ├── calendar.py            # Google Calendar link builder
│   ├── places.py              # Google Places search
│   ├── state.py               # Conversation state machine
│   ├── ranking.py             # Multi-call result ranking
│   └── twilio.py              # WhatsApp via Meta Cloud API
└── schemas/
    ├── intent.py              # Intent / entity schemas
    └── tools.py               # Voice agent tool schemas
```

<br>

## Getting Started

### Prerequisites

- Python 3.12+
- Docker & Docker Compose
- [ngrok](https://ngrok.com) for webhook tunneling
- API keys: **Twilio**, **ElevenLabs**, **Meta WhatsApp**, **OpenAI**, **Google Places**

### Setup

```bash
# Clone
git clone https://github.com/your-username/vocero.git && cd vocero

# Configure
cp .env.example .env   # then fill in your API keys

# Run (pick one)
docker compose up --build                  # with Docker
pip install -r requirements.txt && uvicorn app.main:app --reload   # without Docker

# Expose for webhooks
ngrok http 8000
```

Then point your webhooks to the ngrok URL:

| Service | Webhook URL |
|---|---|
| Meta WhatsApp | `{ngrok}/api/whatsapp` |
| Twilio | `{ngrok}/api/call-status` |
| ElevenLabs | `{ngrok}/api/tools/*` |

<br>

## How Calls Work

```
1. POST /v1/convai/twilio/register-call  →  ElevenLabs returns TwiML
2. Twilio creates call with that TwiML   →  connects directly to ElevenLabs WebSocket
3. Voice agent speaks, negotiates        →  triggers server tools mid-call
4. Call ends                             →  GPT analyzes full transcript
5. Structured summary + calendar link    →  sent to user via WhatsApp
```

No manual audio bridging. Twilio talks directly to ElevenLabs.

<br>

## API Reference

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/whatsapp` | Meta webhook verification |
| `POST` | `/api/whatsapp` | Incoming WhatsApp messages |
| `POST` | `/api/call-status` | Twilio call status callbacks |
| `POST` | `/api/tools/report_available_slots` | Agent reports availability |
| `POST` | `/api/tools/check_user_preference` | Validate slot vs user prefs |
| `POST` | `/api/tools/confirm_booking` | Confirm a booking |
| `POST` | `/api/tools/end_call_no_availability` | Report no availability |
| `GET` | `/health` | Health check |

<br>

## Environment Variables

<details>
<summary>View all variables</summary>

<br>

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
ELEVENLABS_AGENT_ID_EN=
ELEVENLABS_PHONE_NUMBER_ID=

# OpenAI
OPENAI_API_KEY=

# Google Places
GOOGLE_PLACES_API_KEY=

# App
APP_BASE_URL=https://your-ngrok-url.dev
DEBUG=true
```

</details>

<br>

---

<div align="center">

Built for the [ElevenLabs CallPilot Challenge](https://elevenlabs.io)

</div>
