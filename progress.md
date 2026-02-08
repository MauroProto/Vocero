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

### 2026-02-07 — `conversation_state`
- **Summary:** Created `app/services/state.py` with in-memory conversation state machine (dict keyed by WhatsApp number). States: idle, awaiting_provider, calling, awaiting_user_decision, completed. `ConversationState` dataclass tracks status, pending intent/entities, provider info, call IDs, results, last bot message. Public API: `get_state()`, `reset_state()`, `build_context()`, `merge_entities()`. Wired into `app/api/whatsapp.py`: all three message paths (text, voice, contact) now get/update state. Context string from prior state is passed to `extract_intent()` for multi-turn understanding. `_handle_intent()` transitions state based on parsed intent. Contact sharing while `awaiting_provider` auto-transitions to `calling` with confirmation message. Completed conversations auto-reset on next message. Entity merging accumulates details across messages.
- **Test:** Multi-step: "Necesito dentista mañana" → state=awaiting_provider → share contact → state=calling with confirmation. Cancel: "cancel" → state resets to idle. Completed auto-reset: completed state + new message → idle. Direct call: "Call +54... for oil change" → state=calling. Context passed to LLM enables follow-up interpretation ("entre 2 y 4" merges time_preference).

### 2026-02-07 — `outbound_voice_call`
- **Summary:** Created `app/services/elevenlabs_call.py` with `make_outbound_call()` using ElevenLabs native Twilio integration (`client.conversational_ai.twilio.outbound_call()`). Takes to_number and optional dynamic_variables (language, service_type, date/time preferences). Returns (conversation_id, call_sid). Singleton AsyncElevenLabs client. Added `elevenlabs_phone_number_id` to config.py and .env.example. Wired into whatsapp.py: when state transitions to CALLING, `asyncio.create_task(_trigger_call())` fires in background — sends "Calling..." WhatsApp message, places call, stores IDs in state.
- **Test:** App imports cleanly. Routes registered. `_trigger_call` sends progress message + places call or sends failure notification.

### 2026-02-07 — `voice_agent_tools`
- **Summary:** Created `app/api/tools.py` with 4 server tool webhooks under `/api/tools/`: `report_available_slots` (agent reports provider slots, sends WhatsApp update), `check_user_preference` (validates slot against user's date/time preferences), `confirm_booking` (records booking, sends formatted confirmation, marks state completed), `end_call_no_availability` (notifies user, marks completed). Created `app/schemas/tools.py` with Pydantic models for all requests/responses. All endpoints use `find_state_by_conversation_id()` to look up user by active conversation. Registered router in main.py.
- **Test:** All 4 endpoints registered at `/api/tools/*`. Return valid JSON. Use conversation_id to find user state and send WhatsApp notifications.

### 2026-02-07 — `realtime_progress` + `structured_whatsapp_response`
- **Summary:** Created `app/services/messages.py` with bilingual (EN/ES) message formatters: `format_calling_message()`, `format_slots_available()`, `format_no_availability()`, `format_booking_confirmed()` (with provider, datetime, address, notes), `format_call_failed()`. Uses WhatsApp *bold* formatting. Progress messages sent from: whatsapp.py `_trigger_call()` (calling...), tools.py webhooks (availability/booking/no-availability), callbacks.py (call failed/busy/no-answer). Added `find_state_by_conversation_id()` to state.py for reverse lookup. Implemented call-status callback in callbacks.py for Twilio status updates.
- **Test:** App starts cleanly. All routes registered. Message formatters produce correct bilingual output.

### 2026-02-07 — `elevenlabs_agent_setup`
- **Summary:** Configured ElevenLabs Phone Agent via API. Updated TTS model from `eleven_turbo_v2` to `eleven_turbo_v2_5` (required for non-English). Set language to `es`. Updated voice to Spanish voice (`tomkxGQGz4b1kE0EM722`). Rewrote agent prompt in Argentine Spanish (instructions for calling providers, using tools). Set first message: "Hola, buen día. Llamo de parte de un cliente para consultar por {{service_type}}..." Created 4 webhook tools as standalone resources via `POST /v1/convai/tools` and attached via `tool_ids`: `report_available_slots`, `check_user_preference`, `confirm_booking`, `end_call_no_availability`. All point to ngrok URL. Fixed dynamic variable names to match our code (`provider_name`, `service_type`, `date_preference`, `time_preference`, `special_requests`). Updated local tool schemas to match ElevenLabs tool schemas (separate date/time fields instead of single datetime).
- **Test:** Agent config verified via GET API: language=es, TTS=eleven_turbo_v2_5, 4 tools attached, prompt in Spanish. All 4 local tool endpoints return 200 with correct JSON.

### 2026-02-07 — Dynamic Variables Fix + Prompt Rewrite + `escalate_to_user` + `google_places_search`
- **Summary:** Four-phase fix based on real testing feedback.
  - **Phase 1 (Dynamic Vars):** Added `user_name` and `search_results` to `ConversationState`. Store WhatsApp `profile_name` as `state.user_name`. Fixed dynamic variable names: `date_preference` → `preferred_date`, `time_preference` → `preferred_time`. Now sends `user_name` to ElevenLabs agent.
  - **Phase 2 (Prompt Rewrite):** Complete rewrite of `elevenlabs_agent_prompt.md`. Agent now calls AS the user ("Habla Juan") instead of "on behalf of". Only references 4 existing tools (removed `escalate_to_user` from prompt until backend is live). Less scripted, more natural conversation guidelines. Simple first message.
  - **Phase 3 (Escalate to User):** Created `app/services/escalation.py` with `asyncio.Event`-based blocking. New `POST /api/tools/escalate_to_user` endpoint blocks up to 55s waiting for user's WhatsApp reply. WhatsApp handler intercepts replies when state is `AWAITING_USER_DECISION`, resolves the event. Supports text and audio replies. Added `EscalateToUserRequest`/`EscalateToUserResponse` schemas.
  - **Phase 4 (Google Places):** Created `app/services/places.py` using Google Places API (New) Text Search. Added `SEARCH_PROVIDERS` intent. Updated intent parser with search description and classification rules. Created `format_search_results()` for formatted WhatsApp output. Handles search result selection by number → triggers call.
- **Files changed:** `state.py`, `whatsapp.py`, `tools.py`, `intent.py`, `messages.py`, `config.py`, `intent.py` (schema), `tools.py` (schema), `.env.example`, `elevenlabs_agent_prompt.md`. New: `escalation.py`, `places.py`.
- **Test:** Requires live testing: (1) Check logs for correct dynamic variables with `user_name`. (2) Copy new prompt to ElevenLabs → test call sounds natural. (3) Register `escalate_to_user` tool in ElevenLabs → test mid-call escalation. (4) Set `GOOGLE_PLACES_API_KEY` → "busco dentista en Palermo" returns results → pick one → call triggers.
