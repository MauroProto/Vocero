# Domain Overview

## Core Entities

### User
- Identified by WhatsApp phone number (from Twilio).
- Optional email for transcript delivery.
- Can have multiple appointment requests.

### AppointmentRequest
- Created when user sends a message requesting an appointment.
- Contains: service type, time preferences, location preferences, special notes.
- Status lifecycle: `pending` → `calling` → `booked` / `failed` / `cancelled`.

### CallLog
- One per outbound call to a provider.
- Linked to an AppointmentRequest.
- Contains: provider phone/name, call status, duration, transcript, outcome.
- Status: `initiated` → `in_progress` → `completed` / `failed` / `no_answer`.

### Appointment (booked result)
- Created when a call successfully books a slot.
- Contains: provider name, date/time, address, any confirmation details.
- Linked to CallLog and AppointmentRequest.

## Entity Relationships

```
User  1──────N  AppointmentRequest
                      │
                      1
                      │
                      N
                  CallLog
                      │
                      0..1
                      │
                  Appointment
```

## User Journeys

### 1. Simple Booking (Single Provider)
1. User sends: "I need a haircut tomorrow afternoon"
2. Bot extracts intent → service: hairdresser, time: tomorrow PM
3. Bot asks for provider preference or uses a known provider
4. Places outbound call via ElevenLabs agent
5. Agent negotiates slot, books appointment
6. User receives WhatsApp: "Booked at Salon X, tomorrow 3:00 PM, 123 Main St"

### 2. Voice Note Booking
1. User sends voice note describing their need
2. Bot transcribes audio → text
3. Continues as text flow from step 2 above

### 3. Multi-Provider Search
1. User sends: "Find me the earliest dentist appointment this week"
2. Bot calls multiple dentists in parallel
3. Aggregates results, ranks by earliest availability
4. Sends ranked list to user
5. User picks one → bot confirms

### 4. Transcript Request
1. After any completed call, user can say "send me the transcript"
2. Bot asks for email (or uses stored email)
3. Sends full transcript via Resend
