# Agentic Functions — Diseño Detallado

Este es el corazón de lo que evalúa ElevenLabs. Acá definimos exactamente qué herramientas tiene el agente de voz y cómo las usa.

---

## 1. Herramientas del Agente

### 1.1 validate_slot

**Propósito**: Verificar si un horario propuesto por la recepcionista es aceptable para el usuario.

**Configuración en ElevenLabs Dashboard:**
- **Type**: Webhook (Server Tool)
- **Name**: `validate_slot`
- **Description**: `Validates if a proposed appointment date and time are acceptable for the user. Call this tool EVERY TIME the receptionist offers a specific time slot, BEFORE accepting or rejecting it.`
- **URL**: `https://TU_NGROK_URL/api/tools/validate_slot`
- **Method**: POST

**Parámetros:**

| Nombre | Tipo | Requerido | Descripción |
|--------|------|-----------|-------------|
| `date` | string | sí | `The proposed appointment date. Use YYYY-MM-DD format if possible, or describe it as the receptionist said it (e.g., "Wednesday", "next Monday")` |
| `time` | string | sí | `The proposed appointment time. Use HH:MM format if possible, or describe it as said (e.g., "3 PM", "morning")` |
| `professional_name` | string | no | `Name of the professional or doctor if mentioned` |

**Tu backend recibe:**
```json
{
    "date": "2025-03-12",
    "time": "15:00",
    "professional_name": "Dr. García"
}
```

**Tu backend responde:**
```json
{
    "valid": true,
    "message": "The time slot is acceptable for the user."
}
```
O si no es válido:
```json
{
    "valid": false,
    "message": "The user prefers morning appointments. Please ask for an earlier time."
}
```

**Implementación en tu backend:**

```python
@router.post("/validate_slot")
async def validate_slot(request: Request) -> dict:
    data = await request.json()
    date = data.get("date", "")
    time_str = data.get("time", "")

    # Obtener el contexto de la llamada actual
    # (quién está llamando, qué preferencias tiene el usuario)
    call_context = get_current_call_context(request)

    if not call_context:
        return {"valid": True, "message": "No preferences set, any time is fine."}

    prefs = call_context.user_preferences

    # Validar contra preferencias del usuario
    if prefs.time_preference:
        if prefs.time_preference == "mañana" and _is_afternoon(time_str):
            return {
                "valid": False,
                "message": f"The user prefers morning appointments. Ask for a time before 12:00."
            }
        elif prefs.time_preference == "tarde" and _is_morning(time_str):
            return {
                "valid": False,
                "message": f"The user prefers afternoon appointments. Ask for a time after 12:00."
            }

    return {"valid": True, "message": "The time slot is acceptable."}
```

---

### 1.2 report_result

**Propósito**: Informar al backend el resultado de la llamada (éxito o fracaso).

**Configuración en ElevenLabs Dashboard:**
- **Type**: Webhook (Server Tool)
- **Name**: `report_result`
- **Description**: `Reports the final result of the phone call. Call this tool ONCE when the conversation is ending - either after successfully booking an appointment, or when it's clear that booking won't be possible.`
- **URL**: `https://TU_NGROK_URL/api/tools/report_result`
- **Method**: POST

**Parámetros:**

| Nombre | Tipo | Requerido | Descripción |
|--------|------|-----------|-------------|
| `status` | string | sí | `The outcome: "booked" if appointment was scheduled, "no_availability" if no slots available, "callback_needed" if they asked to call back later, "wrong_number" if wrong place, "closed" if they are closed, "failed" if could not complete for other reason` |
| `date` | string | no | `Appointment date if booked (YYYY-MM-DD or as said)` |
| `time` | string | no | `Appointment time if booked (HH:MM or as said)` |
| `professional_name` | string | no | `Name of the assigned professional/doctor` |
| `notes` | string | no | `Any additional notes or requirements mentioned (e.g., "bring ID", "arrive 15 min early", "fasting required")` |
| `instructions` | string | no | `Special instructions from the provider` |

**Tu backend recibe (ejemplo exitoso):**
```json
{
    "status": "booked",
    "date": "2025-03-12",
    "time": "15:00",
    "professional_name": "Dr. García",
    "notes": "Consulta de rutina",
    "instructions": "Llegar 10 minutos antes con DNI"
}
```

**Tu backend recibe (ejemplo sin disponibilidad):**
```json
{
    "status": "no_availability",
    "notes": "No tienen turnos hasta la semana que viene"
}
```

**Tu backend responde:**
```json
{
    "success": true,
    "message": "Result recorded. The user will be notified."
}
```

**Implementación en tu backend:**

```python
from app.services.whatsapp import send_whatsapp

@router.post("/report_result")
async def report_result(request: Request) -> dict:
    data = await request.json()

    result = CallResult(
        status=data.get("status", "failed"),
        date=data.get("date"),
        time=data.get("time"),
        professional_name=data.get("professional_name"),
        notes=data.get("notes"),
        instructions=data.get("instructions"),
    )

    # Buscar a qué usuario corresponde esta llamada
    call_context = get_current_call_context(request)
    user_phone = call_context.user_phone

    # Formatear y enviar resultado por WhatsApp
    message = format_call_result(result, call_context.provider_name)
    send_whatsapp(user_phone, message)

    # Actualizar estado
    conversation = await get_conversation(user_phone)
    conversation.call_results.append(result)
    conversation.status = ConversationStatus.IDLE

    return {"success": True, "message": "Result recorded."}


def format_call_result(result: CallResult, provider_name: str) -> str:
    """Formatear resultado de llamada para WhatsApp."""

    if result.status == "booked":
        msg = f"""✅ *¡Turno agendado!*

📍 *{provider_name}*
📅 {result.date}
🕐 {result.time}"""

        if result.professional_name:
            msg += f"\n👨‍⚕️ {result.professional_name}"
        if result.instructions:
            msg += f"\n\n📋 *Instrucciones:* {result.instructions}"
        if result.notes:
            msg += f"\n📝 {result.notes}"

        return msg

    elif result.status == "no_availability":
        msg = f"❌ *{provider_name}* no tiene turnos disponibles."
        if result.notes:
            msg += f"\n📝 {result.notes}"
        msg += "\n\n¿Querés que pruebe con otro lugar?"
        return msg

    elif result.status == "callback_needed":
        return f"📞 *{provider_name}* pide que llamemos más tarde.\n📝 {result.notes or ''}\n\n¿Querés que intente con otro lugar?"

    elif result.status == "wrong_number":
        return f"⚠️ El número no corresponde a *{provider_name}*. ¿Querés buscar otro?"

    elif result.status == "closed":
        return f"🔒 *{provider_name}* está cerrado en este momento.\n\n¿Querés que pruebe con otro lugar?"

    else:
        return f"⚠️ No pude completar la llamada a *{provider_name}*.\n\n¿Querés que lo intente de nuevo o busque otro lugar?"
```

---

### 1.3 ask_user (STRETCH GOAL)

**Propósito**: Consultar al usuario via WhatsApp cuando el agente necesita información que no tiene.

**Nota**: Esto es complejo porque requiere pausar la llamada telefónica mientras se espera la respuesta de WhatsApp. Solo implementar si sobra tiempo.

**Configuración:**
- **Name**: `ask_user`
- **Description**: `Ask the user a question via WhatsApp when you need information you don't have. Use this ONLY when the receptionist asks for something you cannot answer (e.g., insurance number, patient full name, specific doctor preference). The user will respond via WhatsApp and you'll receive their answer.`
- **URL**: `https://TU_NGROK_URL/api/tools/ask_user`

**Parámetros:**

| Nombre | Tipo | Requerido | Descripción |
|--------|------|-----------|-------------|
| `question` | string | sí | `The question to ask the user, in Spanish` |

---

## 2. System Prompt del Agente de Voz

Este es el prompt que le da al agente de ElevenLabs su personalidad y comportamiento. Se puede configurar como prompt base del agente, y después hacer override parcial por llamada.

### Prompt Base del Agente

```
Sos Vocero, un asistente virtual que llama a negocios para agendar turnos en nombre de usuarios.

## Tu personalidad
- Hablás en español argentino, con tono amable y profesional
- Sos cortés pero directo, no das vueltas innecesarias
- Si no entendés algo, pedís que lo repitan amablemente
- Nunca inventás información que no tenés
- Si la recepcionista te hace una pregunta que no podés responder, decí honestamente que vas a consultar y lo confirmás

## Tu objetivo
Agendar un turno según las preferencias del usuario. Si no hay disponibilidad exacta, negociá la opción más cercana.

## Flujo de la llamada
1. Saludá amablemente y decí que llamás para pedir un turno
2. Mencioná el tipo de servicio que necesitás
3. Mencioná la fecha y horario preferidos
4. Escuchá lo que te ofrece la recepcionista
5. SIEMPRE usá validate_slot para verificar si el horario ofrecido es aceptable
6. Si es aceptable, confirmá el turno y pedí los datos (día, hora, con quién, instrucciones)
7. Agradecé amablemente
8. Usá report_result para informar el resultado

## Reglas importantes
- NUNCA aceptes un horario sin usar validate_slot primero
- SIEMPRE usá report_result al terminar la llamada, sin importar el resultado
- Si no hay turnos, preguntá cuándo sería la próxima disponibilidad
- Si la persona dice que es número equivocado, disculpate y usá report_result con status "wrong_number"
- Si no contestan o es contestador, esperá 10 segundos y usá report_result con status "no_answer"
- Si la recepcionista pide información que no tenés, intentá resolver o usá ask_user si está disponible
- Mantené la llamada breve y eficiente, no más de 3 minutos
```

### Override por Llamada (contexto específico)

Cuando se inicia cada llamada, se agrega contexto específico al prompt via `conversation_config_override`:

```python
call_prompt = f"""
## Contexto de esta llamada
- Estás llamando a: {provider_name}
- Servicio solicitado: {service_type}
- Fecha preferida: {date_preference or "cualquier día de esta semana"}
- Horario preferido: {time_preference or "cualquier horario"}
- Nombre del paciente/cliente: {user_name or "no proporcionado"}
- Pedido especial: {specific_request or "ninguno"}
"""
```

### Primer Mensaje del Agente

El primer mensaje es lo primero que dice el agente cuando la recepcionista atiende:

```python
first_message = f"Hola, buenas tardes. Llamo para consultar si tienen disponibilidad para un turno de {service_type}, preferentemente {date_preference or 'esta semana'}{' por la ' + time_preference if time_preference else ''}."
```

---

## 3. Configuración de Tools en el Dashboard

### Paso a paso para configurar validate_slot

1. Dashboard → Tu Agente → Tools → Add Tool
2. Seleccionar "Webhook"
3. Name: `validate_slot`
4. Description: (copiar de arriba)
5. URL: `https://TU_NGROK_URL/api/tools/validate_slot`
6. Method: POST
7. Headers: `Content-Type: application/json`
8. Body Parameters:
   - Add Parameter → name: `date`, type: `string`, required: true, description: (copiar de arriba)
   - Add Parameter → name: `time`, type: `string`, required: true, description: (copiar de arriba)
   - Add Parameter → name: `professional_name`, type: `string`, required: false, description: (copiar de arriba)

9. Repetir para `report_result` con sus parámetros

### System Tool: End Conversation

También agregar el system tool "End conversation":
1. Dashboard → Tu Agente → Tools → Add Tool
2. Seleccionar "End Conversation"
3. Description: "End the phone call after reporting the result"

---

## 4. Testing de Tools

ElevenLabs permite testear tools con mock responses:

1. En el dashboard, ir a "Test" o "Playground"
2. Configurar `tool_mock_config` para simular respuestas de tus webhooks
3. Probar que el agente:
   - Llama a validate_slot cuando la recepcionista ofrece un horario
   - Llama a report_result al terminar
   - Usa el system tool End Conversation después de report_result
   - No inventa información

### Mock config ejemplo

```json
{
    "validate_slot": {
        "response": {
            "valid": true,
            "message": "The time slot is acceptable."
        }
    },
    "report_result": {
        "response": {
            "success": true,
            "message": "Result recorded."
        }
    }
}
```

---

## 5. Vincular Llamada con Usuario

Cuando ElevenLabs hace un POST a tus tools, necesitás saber a qué usuario corresponde esa llamada. Opciones:

### Opción A: Usar conversation_id

Cuando iniciás la llamada saliente, la API devuelve `conversation_id`. Guardar el mapeo:

```python
# Al iniciar la llamada
call_mapping: dict[str, str] = {}  # conversation_id -> user_phone

response = await make_outbound_call(...)
call_mapping[response["conversation_id"]] = user_phone
```

ElevenLabs pasa el `conversation_id` en los headers del webhook.

### Opción B: Usar custom parameters / dynamic variables

Pasar el user_phone como variable dinámica:

```python
{
    "conversation_initiation_client_data": {
        "dynamic_variables": {
            "user_phone": "+5491155556666",
            "call_id": "call_123"
        }
    }
}
```

Y en la URL del tool incluir la variable:
```
https://TU_NGROK_URL/api/tools/report_result?call_id={{call_id}}
```

O pasar `call_id` como parámetro del tool que el agente siempre envía.

---

## 6. Tips para el Jurado

1. **Demostrar que validate_slot funciona**: Mostrar un caso donde el agente rechaza un horario porque no coincide con la preferencia del usuario, y pide otro.
2. **report_result con distintos status**: Mostrar que el agente reporta correctamente tanto éxitos como fracasos.
3. **El agente toma decisiones**: Enfatizar que el agente no sigue un script fijo, sino que reacciona dinámicamente a lo que dice la recepcionista.
4. **Logging visible**: Tener un log en consola que muestre cada tool call en tiempo real durante el demo.
