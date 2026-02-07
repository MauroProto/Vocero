# Vocero — Progress Log

> Append entries here after completing each feature. Format: date, feature ID, summary, test results.

---

### 2026-02-07 — `app_skeleton`
- **Summary:** Fixed `DATABASE_URL` override in `docker-compose.yml` so the app container connects to the `db` service (host `db`) instead of `localhost`. All scaffolding (FastAPI, SQLAlchemy, Pydantic Settings, Dockerfile, Docker Compose) was already in place.
- **Test:** `docker compose up --build` → clean startup. `GET /health` → `{"status": "ok"}` (200).

### 2026-02-07 — `whatsapp_webhook`
- **Summary:** Implemented `POST /api/whatsapp` webhook handler. Parses Twilio form-encoded POST (From, Body, NumMedia, MediaUrl0, MediaContentType0, ProfileName). Validates Twilio signature (skipped in debug mode). Classifies messages into text, voice_note, or contact types. Echoes text messages back via TwiML. Created `app/services/twilio.py` with async `send_whatsapp_message()` for future REST API messaging. Added basic logging config to `main.py`.
- **Test:** `POST /api/whatsapp` with text → `Echo: Hello Vocero` TwiML (200). Voice note → acknowledged. Contact → acknowledged. Logs show parsed message details.

### 2026-02-07 — `contact_parsing`
- **Summary:** Created `app/services/contact.py` with vCard parsing (`parse_vcard`, `download_and_parse_vcard`) and phone regex extraction (`extract_phone_from_text`). Integrated into webhook: shared contacts download+parse vCard, text messages check for embedded phone numbers first. Graceful error handling for unreachable/unparseable vCards.
- **Test:** vCard `FN:Dr. Juan Pérez / TEL:+54 9 11 2233-4455` → parsed correctly. Text `+54 9 11 5555-6789` → extracted `+5491155556789`. Text without phone → echo. Failed vCard download → user-friendly fallback message.

### 2026-02-07 — `voice_note_processing`
- **Summary:** Created `app/services/transcription.py` with `download_media()` (Twilio auth) and `transcribe_audio()` (ElevenLabs Scribe V2, auto language detection). Upgraded `elevenlabs` SDK from 1.50.5 to 2.34.0 for STT support. Webhook now downloads voice notes and returns transcription with detected language.
- **Test:** STT API call with WAV audio → returns `TranscriptionResult(text, language, probability)`. Silence → empty text. Tone → empty text. Text/contact paths still work.

### 2026-02-07 — `intent_parsing`
- **Summary:** Created `app/schemas/intent.py` (IntentType, Language, Entities, IntentResult) and `app/services/intent.py` (GPT-4.1-mini via httpx with structured output JSON schema). Bilingual system prompt classifies 5 intents (call_number, request_appointment, confirm, cancel, help) and extracts 7 entity types. LLM generates response_message in the user's detected language. Integrated into webhook: TEXT path calls `extract_intent()` instead of echo/phone-extract, VOICE_NOTE path pipes transcription through intent parsing. Falls back to echo on OpenAI failure. Added `openai_api_key` to config. Removed unused `extract_phone_from_text` import.
- **Test:** Spanish appointment request → intent=request_appointment, language=es, response asks for provider contact. English message → intent=request_appointment, entities populated. Phone number in text → intent=call_number. "yes" → intent=confirm. "cancel" → intent=cancel. OpenAI timeout → graceful fallback to echo.
