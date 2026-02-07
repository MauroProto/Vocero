# Twilio Voz + ElevenLabs — La Integración Crítica

Este es el componente más importante y más riesgoso del proyecto. Hay **dos opciones** para hacer llamadas. Recomendamos empezar con la Opción A.

---

## Opción A: Integración Nativa de ElevenLabs (RECOMENDADA)

ElevenLabs tiene una integración nativa con Twilio que maneja todo el bridge de audio internamente. No necesitás escribir código de WebSocket.

### Setup

1. **Importar número de Twilio en ElevenLabs:**
   - Dashboard → Phone Numbers → Import from Twilio
   - Ingresar: Twilio Phone Number, Account SID, Auth Token
   - ElevenLabs configura automáticamente los webhooks en Twilio

2. **Vincular con el agente:**
   - Dashboard → Tu Agente → Phone Numbers → Seleccionar el número importado

3. **Hacer llamada saliente via API:**

```python
import httpx

async def make_outbound_call(
    http_client: httpx.AsyncClient,
    to_number: str,
    custom_prompt: str,
    first_message: str,
) -> dict:
    """Hacer una llamada saliente usando la integración nativa ElevenLabs-Twilio."""

    response = await http_client.post(
        "https://api.elevenlabs.io/v1/convai/twilio/outbound-call",
        headers={
            "xi-api-key": ELEVENLABS_API_KEY,
            "Content-Type": "application/json",
        },
        json={
            "agent_id": ELEVENLABS_AGENT_ID,
            "agent_phone_number_id": ELEVENLABS_PHONE_NUMBER_ID,
            "to_number": to_number,
            "conversation_initiation_client_data": {
                "conversation_config_override": {
                    "agent": {
                        "prompt": {
                            "prompt": custom_prompt
                        },
                        "first_message": first_message
                    }
                }
            }
        },
        timeout=30.0
    )
    response.raise_for_status()
    return response.json()
    # Returns: {"success": true, "conversation_id": "...", "callSid": "..."}
```

### Ventajas de la Opción A

- Zero código de WebSocket/bridge
- ElevenLabs maneja la conversión de audio
- Menos puntos de fallo
- Setup en minutos, no horas

### Cómo obtener el resultado de la llamada

Cuando la llamada termina, el agente invoca el server tool `report_result` que hace un POST a tu backend con los datos del resultado. Ver **07_AGENTIC_FUNCTIONS.md**.

Además, ElevenLabs tiene **post-call webhooks** que se envían cuando la conversación termina:
- Dashboard → Agente → Analysis → Post-call webhook URL
- Te envía la transcripción completa, duración, y metadata

### Personalizar por llamada con variables dinámicas

Podés pasar variables dinámicas que se inyectan en el prompt:

```python
{
    "conversation_initiation_client_data": {
        "dynamic_variables": {
            "service_type": "dentista",
            "preferred_date": "mañana",
            "preferred_time": "por la tarde",
            "user_name": "Mauro",
            "special_requests": "consulta de rutina"
        }
    }
}
```

Y en el system prompt del agente referenciás las variables:
```
Estás llamando para pedir un turno de {{service_type}} para {{user_name}}.
El usuario prefiere {{preferred_date}} {{preferred_time}}.
Pedido especial: {{special_requests}}.
```

---

## Opción B: Bridge WebSocket Manual (MÁS CONTROL)

Si la Opción A no funciona o necesitás más control, podés hacer el bridge ustedes mismos.

### Arquitectura

```
Teléfono del negocio
    ↕ (audio de voz)
Twilio Voice
    ↕ (WebSocket Media Streams - audio mulaw base64)
Tu servidor FastAPI (bridge)
    ↕ (WebSocket - audio base64)
ElevenLabs Conversational AI
```

### Paso 1: Iniciar llamada saliente con Twilio

```python
from twilio.rest import Client

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

def start_outbound_call(to_number: str, call_id: str):
    """Inicia una llamada saliente. Twilio va a hacer un POST a /webhook/voice/outbound
    para obtener las instrucciones TwiML."""

    call = twilio_client.calls.create(
        to=to_number,
        from_=TWILIO_PHONE_NUMBER,
        url=f"{BASE_URL}/webhook/voice/outbound?call_id={call_id}",
        method="POST",
        status_callback=f"{BASE_URL}/webhook/voice/status",
        status_callback_event=["completed", "failed", "no-answer", "busy"],
    )
    return call.sid
```

### Paso 2: TwiML que conecta a WebSocket

Cuando Twilio hace el POST a `/webhook/voice/outbound`, responder con TwiML que abre un Media Stream:

```python
@router.post("/voice/outbound")
async def voice_outbound(request: Request) -> Response:
    form_data = await request.form()
    call_id = request.query_params.get("call_id", "")

    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <Stream url="wss://{NGROK_DOMAIN}/ws/media-stream/{call_id}">
            <Parameter name="call_id" value="{call_id}" />
        </Stream>
    </Connect>
</Response>"""

    return Response(content=twiml, media_type="application/xml")
```

### Paso 3: WebSocket Bridge

Este es el servidor WebSocket que actúa como puente entre Twilio y ElevenLabs:

```python
import asyncio
import json
import base64
import websockets
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

@router.websocket("/ws/media-stream/{call_id}")
async def media_stream_bridge(websocket: WebSocket, call_id: str):
    """Bridge bidireccional entre Twilio Media Streams y ElevenLabs WebSocket."""
    await websocket.accept()

    stream_sid = None
    elevenlabs_ws = None

    try:
        # 1. Obtener signed URL de ElevenLabs
        signed_url = await get_elevenlabs_signed_url()

        # 2. Conectar a ElevenLabs WebSocket
        elevenlabs_ws = await websockets.connect(signed_url)

        # 3. Enviar configuración inicial a ElevenLabs
        await elevenlabs_ws.send(json.dumps({
            "type": "conversation_initiation_client_data",
            "conversation_config_override": {
                "agent": {
                    "prompt": {
                        "prompt": get_call_prompt(call_id)
                    },
                    "first_message": get_first_message(call_id)
                }
            }
        }))

        # 4. Crear tareas para audio bidireccional
        async def twilio_to_elevenlabs():
            """Reenviar audio de Twilio a ElevenLabs."""
            try:
                while True:
                    data = await websocket.receive_text()
                    msg = json.loads(data)

                    if msg["event"] == "start":
                        nonlocal stream_sid
                        stream_sid = msg["start"]["streamSid"]

                    elif msg["event"] == "media":
                        # Audio de Twilio viene en mulaw base64
                        audio_b64 = msg["media"]["payload"]
                        await elevenlabs_ws.send(json.dumps({
                            "user_audio_chunk": audio_b64
                        }))

                    elif msg["event"] == "stop":
                        break
            except WebSocketDisconnect:
                pass

        async def elevenlabs_to_twilio():
            """Reenviar audio de ElevenLabs a Twilio."""
            try:
                async for message in elevenlabs_ws:
                    data = json.loads(message)

                    if data.get("type") == "audio":
                        # Audio de ElevenLabs, reenviar a Twilio
                        audio_b64 = data.get("audio_base64", "")
                        if audio_b64 and stream_sid:
                            await websocket.send_text(json.dumps({
                                "event": "media",
                                "streamSid": stream_sid,
                                "media": {
                                    "payload": audio_b64
                                }
                            }))

                    elif data.get("type") == "tool_call":
                        # El agente quiere usar una herramienta
                        result = await handle_tool_call(call_id, data)
                        await elevenlabs_ws.send(json.dumps({
                            "type": "tool_call_result",
                            "tool_call_id": data["tool_call_id"],
                            "result": result
                        }))
            except websockets.ConnectionClosed:
                pass

        # 5. Ejecutar ambas tareas en paralelo
        await asyncio.gather(
            twilio_to_elevenlabs(),
            elevenlabs_to_twilio()
        )

    except Exception as e:
        print(f"Error en media stream bridge: {e}")
    finally:
        if elevenlabs_ws:
            await elevenlabs_ws.close()
```

### Formato de Audio

| Componente | Formato | Sample Rate | Encoding |
|-----------|---------|-------------|----------|
| Twilio Media Streams | mulaw | 8kHz | base64 |
| ElevenLabs WebSocket | Configurable (PCM/mulaw) | Configurable | base64 |

**Importante**: Verificar que ElevenLabs acepte mulaw 8kHz directamente. Si no, hay que convertir entre formatos (lo cual agrega complejidad y latencia).

---

## Opción C: Simulación (PLAN B)

Si ni A ni B funcionan, simular con dos agentes de ElevenLabs.

### Arquitectura de simulación

```
Agente Vocero (ElevenLabs) ← → Agente Recepcionista (ElevenLabs)
         ↕                                ↕
     Tu backend (orquestador)
```

### Implementación

1. Crear dos agentes en ElevenLabs:
   - **Agente Vocero**: El que pide turno
   - **Agente Recepcionista**: Simula la recepcionista del negocio

2. Usar la API de "Simulate Conversations" de ElevenLabs:
   - https://elevenlabs.io/docs/agents-platform/guides/simulate-conversations

3. Grabar el audio de la conversación para reproducir en el demo

### Ventajas del Plan C
- Funciona sin Twilio Voice
- Demuestra las Agentic Functions igual
- Se puede preparar previamente un resultado controlado
- Para el jurado, el valor es la conversación natural + tool calling

---

## Monitorear Llamadas

### Status Callback de Twilio

```python
@router.post("/voice/status")
async def voice_status(request: Request):
    """Twilio envía actualizaciones de estado de la llamada."""
    form_data = await request.form()

    call_sid = form_data.get("CallSid", "")
    call_status = form_data.get("CallStatus", "")
    # Estados: initiated, ringing, answered, completed, busy, no-answer, failed

    if call_status == "completed":
        duration = form_data.get("CallDuration", "0")
        # Notificar al usuario que la llamada terminó

    elif call_status in ("busy", "no-answer", "failed"):
        # Notificar al usuario que no se pudo conectar

    return Response(content="OK", media_type="text/plain")
```

### Post-Call Webhook de ElevenLabs

Configurar en el dashboard del agente:
- URL: `https://TU_NGROK_URL/api/elevenlabs/post-call`
- Te envía: transcripción completa, duración, tool calls realizados, metadata

---

## Recomendación de Implementación

1. **Hora 0-1**: Probar Opción A (integración nativa). Importar número, vincular agente, hacer una llamada de prueba.
2. **Si funciona**: Seguir con Opción A. Implementar el override de prompt por llamada.
3. **Si NO funciona**: Evaluar rápidamente Opción B (máx 2 horas de intento).
4. **Si B tampoco**: Ir directo a Opción C (simulación). No perder más tiempo.

## Links de referencia

- ElevenLabs Twilio Integration: https://elevenlabs.io/docs/agents-platform/phone-numbers/twilio-integration/native-integration
- Outbound Call API: https://elevenlabs.io/docs/api-reference/twilio/outbound-call
- Twilio Media Streams: https://www.twilio.com/docs/voice/media-streams
- ElevenLabs + Twilio JS Example: https://github.com/louisjoecodes/elevenlabs-twilio-i-o
- Batch Calling: https://elevenlabs.io/blog/introducing-batch-calling-for-elevenlabs-conversational-ai
- Simulate Conversations: https://elevenlabs.io/docs/agents-platform/guides/simulate-conversations
