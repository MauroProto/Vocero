# ElevenLabs Integration Guide

## Overview

ElevenLabs Agents Platform provides AI voice agents for real-time conversations.
We use TWO separate capabilities:
1. **Outbound calls via Twilio** — native integration, one API call per outbound call
2. **Server tools (webhooks)** — agent calls our FastAPI endpoints mid-conversation

## Native WhatsApp (NOT USED)

ElevenLabs has native WhatsApp integration (launched Dec 2025) connecting directly to Meta WhatsApp Business API. We are NOT using this because it requires a Meta Business Manager account. We use Twilio WhatsApp Sandbox instead.

## Outbound Calls (Native Twilio Integration)

### One-Time Setup
1. Import Twilio phone number into ElevenLabs: Dashboard → Telephony → Phone Numbers → Import from Twilio
2. Enter Twilio Account SID + Auth Token + phone number
3. ElevenLabs auto-configures Twilio webhooks
4. Link the Phone Agent to the phone number

### Making Outbound Calls

```python
from elevenlabs.client import AsyncElevenLabs

client = AsyncElevenLabs(api_key=settings.elevenlabs_api_key)

result = await client.conversational_ai.twilio.outbound_call(
    agent_id="phone-agent-id",
    agent_phone_number_id="imported-twilio-number-id",
    to_number="+1234567890",
    conversation_initiation_client_data={
        "dynamic_variables": {
            "user_name": "John Smith",
            "service_type": "dentist",
            "preferred_time": "Friday afternoon",
            "language": "es",
        }
    }
)
# Returns: conversation_id, callSid
```

### Dynamic Variables
Pass per-call context. Referenced in agent prompt as `{{variable_name}}`.

## Phone Agent Configuration

### System Prompt Strategy
The Phone Agent must:
1. Introduce itself professionally (in user's language)
2. State the appointment need clearly
3. Ask about available time slots
4. Negotiate when slots don't match preferences
5. Use `escalate_to_user` tool when multiple options or decision needed
6. Confirm booking details (date, time, provider name, address)
7. End call politely

### Creating Agent via API

```python
agent = await client.conversational_ai.agents.create(
    name="Vocero Phone Agent",
    conversation_config={
        "agent": {
            "first_message": "Hello, I'm calling on behalf of {{user_name}} to schedule a {{service_type}} appointment. They're looking for {{preferred_time}}.",
            "language": "en"
        },
        "tts": {"voice_id": "VOICE_ID_HERE"}
    },
    prompt={
        "prompt": "...",  # Full system prompt
        "llm": "gpt-4o-mini",
        "tool_ids": ["tool_1", "tool_2"]
    }
)
```

## Server Tools (Webhooks)

The Phone Agent calls these FastAPI endpoints mid-conversation:

| Tool | Endpoint | Purpose |
|------|----------|---------|
| `report_available_slots` | `POST /api/tools/slots` | Agent reports slots offered by provider |
| `check_user_preference` | `POST /api/tools/check-preference` | Validates slot against user's time preference |
| `confirm_booking` | `POST /api/tools/confirm` | Records confirmed appointment |
| `escalate_to_user` | `POST /api/tools/escalate` | Sends WhatsApp to user mid-call for decision |
| `end_call_no_availability` | `POST /api/tools/no-availability` | Marks provider as unavailable |

### Tool Parameter Design
Parameter names/descriptions are critical — the LLM uses them to decide when to invoke.

```json
{
    "name": "report_available_slots",
    "description": "Report available appointment slots offered by the provider.",
    "parameters": {
        "slots": {
            "type": "array",
            "description": "List of available time slots in 'YYYY-MM-DD HH:MM' format"
        },
        "provider_notes": {
            "type": "string",
            "description": "Additional notes from the provider"
        }
    }
}
```

### Tool Latency Constraint
Tool responses must be <500ms to maintain <1s voice response time.

## Getting Transcripts

```python
conversation = await client.conversational_ai.conversations.get(
    conversation_id="conv_abc123"
)
for turn in conversation.transcript:
    print(f"{turn.role}: {turn.message}")
```

Also available: `conversation.analysis.summary`, post-call webhooks.

## Concurrency Limits

| Plan | Concurrent Calls |
|------|-----------------|
| Free/Starter | ~4 |
| Scale | ~10-15 |
| Business | ~30 |

Burst pricing: 3x concurrency at 2x cost.
