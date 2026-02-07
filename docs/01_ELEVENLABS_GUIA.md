# ElevenLabs — Guía Completa para Vocero

## 1. Agents Platform (antes Conversational AI)

ElevenLabs renombró "Conversational AI" a **Agents Platform**. Es la misma tecnología. La documentación actual vive en:
- Overview: https://elevenlabs.io/docs/agents-platform/overview
- Quickstart: https://elevenlabs.io/docs/agents-platform/quickstart

### Qué es

Un sistema para crear agentes de voz AI que pueden:
- Hablar en tiempo real con latencia sub-segundo
- Usar herramientas (tool calling) durante la conversación
- Conectarse a números de teléfono via Twilio
- Hacer llamadas salientes (outbound calls)
- Personalizar voz, idioma, y comportamiento

### LLMs soportados

ElevenLabs permite elegir el LLM que usa el agente internamente. Opciones incluyen:
- GPT-4o, GPT-4o-mini (OpenAI)
- Claude 3.5 Sonnet (Anthropic)
- Gemini (Google)
- LLMs propios de ElevenLabs

Para el hackathon, **GPT-4o-mini** es buena opción por velocidad y costo.

---

## 2. Crear un Agente

### Via Dashboard (recomendado para empezar)

1. Ir a https://elevenlabs.io/app/conversational-ai
2. Click "Create Agent"
3. Configurar:
   - **Name**: Vocero Agent
   - **First message**: "Hola, buenas tardes. Llamo para consultar por un turno."
   - **System prompt**: (ver sección 07_AGENTIC_FUNCTIONS.md para el prompt completo)
   - **Language**: Spanish
   - **Voice**: Elegir una voz en español (ver sección de voces abajo)
   - **LLM**: GPT-4o-mini
4. Agregar Tools (herramientas) — ver sección de Tools abajo
5. Guardar y copiar el **Agent ID**

### Via API

```
POST https://api.elevenlabs.io/v1/convai/agents/create
Headers:
  xi-api-key: TU_ELEVENLABS_API_KEY
  Content-Type: application/json

Body:
{
  "name": "vocero-agent",
  "conversation_config": {
    "agent": {
      "prompt": {
        "prompt": "Sos un asistente que llama a negocios para agendar turnos...",
        "llm": "gpt-4o-mini",
        "temperature": 0.7
      },
      "first_message": "Hola, buenas tardes. Llamo para consultar por un turno.",
      "language": "es"
    },
    "tts": {
      "voice_id": "TU_VOICE_ID"
    }
  }
}
```

Respuesta exitosa devuelve:
```json
{
  "agent_id": "agent_xxxxxxxxxxxx"
}
```

---

## 3. Voces en Español

### Buscar voces en español

En el dashboard de ElevenLabs ir a "Voices" y filtrar por:
- Language: Spanish
- Use case: Conversational

### Voces recomendadas para Vocero

Buscar una voz que suene:
- **Profesional pero cálida** (no robótica)
- **Español latinoamericano** (preferiblemente argentino/neutro)
- **Masculina o femenina** según preferencia

### Via API — listar voces

```
GET https://api.elevenlabs.io/v1/voices
Headers:
  xi-api-key: TU_ELEVENLABS_API_KEY
```

### Professional Voice Cloning (stretch goal)

Si tienen tiempo, pueden clonar una voz propia:
```
POST https://api.elevenlabs.io/v1/voices/add
```
Requiere subir muestras de audio de la voz a clonar.

---

## 4. Tools (Herramientas del Agente)

ElevenLabs tiene 3 tipos de herramientas:

### 4.1 Server Tools (Webhooks) — LOS QUE USAMOS

Son llamadas HTTP que el agente hace a tu backend durante la conversación. El agente decide cuándo llamarlas basándose en la conversación.

**Configuración en el dashboard:**
1. Ir al agente → Tools → Add Tool → Webhook
2. Configurar:
   - **Name**: validate_slot (nombre descriptivo para el LLM)
   - **Description**: "Validates if a proposed appointment slot is acceptable for the user based on their preferences" (descripción clara para que el LLM sepa cuándo usarla)
   - **URL**: https://TU_NGROK_URL/api/tools/validate_slot
   - **Method**: POST
   - **Headers**: Content-Type: application/json
   - **Parameters**: definir los parámetros que el agente debe extraer de la conversación

**Parámetros del tool:**
Cada parámetro tiene:
- `name`: nombre del parámetro (ej: "date")
- `type`: string, number, boolean, etc.
- `description`: descripción para que el LLM sepa qué extraer (ej: "The proposed date in YYYY-MM-DD format")
- `required`: si es obligatorio

**Cómo funciona:**
1. El agente habla con la recepcionista
2. La recepcionista ofrece "el miércoles a las 15:00"
3. El LLM del agente decide que necesita validar ese horario
4. El agente invoca `validate_slot` con `{"date": "2025-03-12", "time": "15:00"}`
5. Tu backend recibe el POST, verifica contra las preferencias del usuario
6. Tu backend responde con `{"valid": true, "message": "El horario es aceptable"}`
7. El agente usa esa respuesta para continuar la conversación

**El agente genera los parámetros dinámicamente** basándose en la conversación y las descripciones de los parámetros. No es un formulario fijo.

### 4.2 Client Tools

Se ejecutan en el cliente (browser/app). **No nos sirven para Vocero** porque no hay cliente web.

### 4.3 System Tools

Herramientas internas del sistema:
- **End conversation**: Terminar la llamada automáticamente
- **Language detection**: Detectar y cambiar idioma automáticamente
- **Transfer call**: Transferir a otro agente o humano

**Para Vocero usamos:**
- `End conversation` — para que el agente pueda colgar cuando termine

---

## 5. WebSocket API

### Connection URL

```
wss://api.elevenlabs.io/v1/convai/conversation?agent_id=TU_AGENT_ID
```

### Autenticación con Signed URL

Para agentes privados/autenticados, primero pedir un signed URL:

```
GET https://api.elevenlabs.io/v1/convai/conversation/get-signed-url?agent_id=TU_AGENT_ID
Headers:
  xi-api-key: TU_ELEVENLABS_API_KEY
```

Respuesta:
```json
{
  "signed_url": "wss://api.elevenlabs.io/v1/convai/conversation?agent_id=xxx&token=yyy"
}
```

- **Validez**: 15 minutos para iniciar la conexión
- **Duración de la conversación**: Sin límite una vez conectado

### Flujo del WebSocket

1. Conectar al signed URL
2. Enviar mensaje de inicialización con configuración
3. Enviar audio del usuario (chunks de audio en base64)
4. Recibir audio del agente (chunks de audio en base64)
5. Recibir eventos de tool calling
6. Responder a tool calls
7. Cerrar conexión

### Formato de audio

- **Entrada (usuario → agente)**: Audio en base64, formato configurable (PCM 16-bit, mulaw)
- **Salida (agente → usuario)**: Audio en base64, mismo formato

---

## 6. Outbound Calls via Twilio (Integración Nativa)

### Opción A: Integración Nativa (MÁS SIMPLE)

ElevenLabs tiene una **integración nativa con Twilio** que simplifica enormemente el setup.

**Setup:**
1. En el dashboard de ElevenLabs → Phone Numbers → Import Twilio Number
2. Ingresar:
   - Twilio Phone Number
   - Twilio Account SID
   - Twilio Auth Token
3. Vincular el número importado con tu agente

**Hacer una llamada saliente (API):**
```
POST https://api.elevenlabs.io/v1/convai/twilio/outbound-call
Headers:
  xi-api-key: TU_ELEVENLABS_API_KEY
  Content-Type: application/json

Body:
{
  "agent_id": "TU_AGENT_ID",
  "agent_phone_number_id": "ID_DEL_NUMERO_IMPORTADO",
  "to_number": "+5411XXXXXXXX",
  "conversation_initiation_client_data": {
    "conversation_config_override": {
      "agent": {
        "prompt": {
          "prompt": "Prompt personalizado para esta llamada específica..."
        },
        "first_message": "Hola, buenas tardes. Llamo para consultar por un turno para dentista."
      }
    }
  }
}
```

**Respuesta exitosa:**
```json
{
  "success": true,
  "message": "Call initiated",
  "conversation_id": "conv_xxxxxxxxxxxx",
  "callSid": "CAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
}
```

**SDKs disponibles:** Python, TypeScript, Go, Ruby, Java, PHP, C#, Swift

### Opción B: Bridge WebSocket (MÁS CONTROL)

Si necesitan más control, pueden hacer el bridge ustedes mismos. Ver **03_TWILIO_VOZ_ELEVENLABS.md**.

### Opción C: Batch Calling (para modo enjambre)

ElevenLabs tiene un feature de **Batch Calling** para iniciar múltiples llamadas simultáneas:
- Útil para el "Swarm Mode" del challenge
- Soporta variables dinámicas por llamada (ej: user_name, service_type)
- Documentación: https://elevenlabs.io/blog/introducing-batch-calling-for-elevenlabs-conversational-ai

---

## 7. Python SDK

### Instalación

```bash
pip install elevenlabs
```

### Uso básico

```python
from elevenlabs import ElevenLabs

client = ElevenLabs(api_key="TU_API_KEY")

# Listar agentes
agents = client.conversational_ai.get_agents()

# Hacer llamada saliente via Twilio
response = client.conversational_ai.twilio.outbound_call(
    agent_id="TU_AGENT_ID",
    agent_phone_number_id="TU_PHONE_ID",
    to_number="+5411XXXXXXXX"
)
print(response.conversation_id)
print(response.call_sid)
```

### Obtener signed URL

```python
signed_url_response = client.conversational_ai.get_signed_url(
    agent_id="TU_AGENT_ID"
)
ws_url = signed_url_response.signed_url
```

---

## 8. Recomendaciones para el Hackathon

1. **Usar la integración nativa Twilio** (Opción A). Es la más rápida de implementar.
2. **Crear el agente via dashboard** primero, probar que funciona, y después hacer overrides via API si hace falta.
3. **El override de prompt por llamada** es clave: permite personalizar el agente para cada llamada específica (qué servicio pedir, para cuándo, etc.)
4. **Probar una llamada saliente lo antes posible** (hora 1-2 del hackathon) para validar que todo funciona.
5. **Usar GPT-4o-mini como LLM del agente** por velocidad.
6. **Agregar el system tool "End conversation"** para que el agente pueda colgar solo.

## 9. Links de referencia

- Dashboard: https://elevenlabs.io/app/conversational-ai
- Docs Overview: https://elevenlabs.io/docs/agents-platform/overview
- Tools: https://elevenlabs.io/docs/agents-platform/customization/tools
- Server Tools: https://elevenlabs.io/docs/agents-platform/customization/tools/server-tools
- Twilio Integration: https://elevenlabs.io/docs/agents-platform/phone-numbers/twilio-integration/native-integration
- Outbound Call API: https://elevenlabs.io/docs/api-reference/twilio/outbound-call
- WebSocket API: https://elevenlabs.io/docs/agents-platform/libraries/web-sockets
- Signed URL: https://elevenlabs.io/docs/agents-platform/api-reference/conversations/get-signed-url
- Python SDK: https://github.com/elevenlabs/elevenlabs-python
- Twilio I/O Example (JS): https://github.com/louisjoecodes/elevenlabs-twilio-i-o
