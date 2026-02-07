# VOCERO — Documentación Técnica

**Índice de documentos para el desarrollo del proyecto.**

Cada documento contiene información investigada, ejemplos de código, y guías paso a paso para implementar cada componente durante el hackathon de 24 horas.

---

## Documentos

| # | Archivo | Contenido |
|---|---------|-----------|
| 01 | [ElevenLabs Guía](./01_ELEVENLABS_GUIA.md) | Agents Platform, Conversational AI, crear agente, voces en español, SDK Python, WebSocket API |
| 02 | [Twilio WhatsApp](./02_TWILIO_WHATSAPP.md) | Sandbox de WhatsApp, webhooks, enviar/recibir mensajes, manejo de audio, FastAPI integration |
| 03 | [Twilio Voz + ElevenLabs](./03_TWILIO_VOZ_ELEVENLABS.md) | La integración crítica: llamadas salientes, WebSocket bridge, audio bidireccional, signed URLs |
| 04 | [Google Places API](./04_GOOGLE_PLACES.md) | Text Search (New), Place Details, field masks, obtener teléfono, Python con httpx |
| 05 | [OpenAI NLU + Whisper](./05_OPENAI_NLU.md) | GPT-4o-mini para NLU, structured output JSON, Whisper API para transcribir audios de WhatsApp |
| 06 | [Arquitectura y Código](./06_ARQUITECTURA_CODIGO.md) | Estructura del proyecto, FastAPI, dependencias, configuración, estado en memoria |
| 07 | [Agentic Functions](./07_AGENTIC_FUNCTIONS.md) | Diseño de validate_slot, report_result, ask_user — schemas JSON, system prompt del agente de voz |
| 08 | [Demo y Preparación](./08_DEMO_PREPARACION.md) | Datos de prueba, recepcionista simulada, guion de demo, slides, checklist pre-hackathon |

---

## Orden de lectura recomendado

1. Empezar por **06_ARQUITECTURA_CODIGO.md** para entender la estructura general
2. Después **02_TWILIO_WHATSAPP.md** (primer componente a implementar)
3. Después **05_OPENAI_NLU.md** (segundo componente)
4. Después **04_GOOGLE_PLACES.md** (tercer componente)
5. Después **01_ELEVENLABS_GUIA.md** y **03_TWILIO_VOZ_ELEVENLABS.md** (el core)
6. Después **07_AGENTIC_FUNCTIONS.md** (las herramientas del agente)
7. Finalmente **08_DEMO_PREPARACION.md** (la demo)

## Links útiles rápidos

- ElevenLabs Dashboard: https://elevenlabs.io/app/conversational-ai
- ElevenLabs Docs: https://elevenlabs.io/docs/agents-platform/overview
- Twilio Console: https://console.twilio.com
- Twilio WhatsApp Sandbox: https://console.twilio.com/us1/develop/sms/try-it-out/whatsapp-learn
- Google Cloud Console: https://console.cloud.google.com
- OpenAI Platform: https://platform.openai.com
- ngrok Dashboard: https://dashboard.ngrok.com
