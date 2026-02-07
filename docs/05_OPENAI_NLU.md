# OpenAI — NLU con GPT-4o-mini + Whisper

## 1. NLU (Natural Language Understanding)

Usamos GPT-4o-mini con Structured Outputs para parsear los mensajes del usuario y extraer intención + entidades.

### Por qué GPT-4o-mini

- **Rápido**: ~300-500ms de latencia para mensajes cortos
- **Barato**: ~$0.15/1M tokens input, ~$0.60/1M tokens output
- **Soporta Structured Outputs**: Fuerza JSON válido en la respuesta
- Para el hackathon, el costo total del NLU va a ser < $0.10

---

## 2. Structured Outputs con Pydantic

### Modelos de datos

```python
from pydantic import BaseModel
from enum import Enum
from typing import Optional

class IntentType(str, Enum):
    CALL_NUMBER = "call_number"           # Usuario pasó un número directo
    SEARCH_AND_CALL = "search_and_call"   # Buscar y llamar
    SEARCH_ONLY = "search_only"           # Solo buscar, no llamar
    CONFIRM = "confirm"                   # Confirmar selección
    CANCEL = "cancel"                     # Cancelar acción
    HELP = "help"                         # Ayuda

class ParsedMessage(BaseModel):
    intent: IntentType
    phone_number: Optional[str] = None
    service_type: Optional[str] = None
    location: Optional[str] = None
    date_preference: Optional[str] = None
    time_preference: Optional[str] = None
    specific_request: Optional[str] = None
    selected_option: Optional[int] = None
```

### System Prompt para el NLU

```python
NLU_SYSTEM_PROMPT = """Sos un parser de mensajes de WhatsApp para un asistente que agenda turnos.
Tu trabajo es extraer la intención y las entidades del mensaje del usuario.

Intenciones posibles:
- call_number: El usuario pasó un número de teléfono y quiere que llamemos. Ejemplo: "Llamá al 4567-8900 y pedí turno para mañana"
- search_and_call: El usuario quiere que busquemos un tipo de negocio y llamemos. Ejemplo: "Necesito un dentista en Palermo para esta semana"
- search_only: El usuario quiere ver opciones antes de decidir. Ejemplo: "Qué peluquerías hay en Belgrano?"
- confirm: El usuario está confirmando algo (eligiendo una opción, aceptando). Ejemplo: "El 1", "Sí", "Dale", "Ese"
- cancel: El usuario quiere cancelar. Ejemplo: "No, cancelá", "Dejá"
- help: El usuario no sabe cómo usar el servicio o no se entiende qué quiere. Ejemplo: "Cómo funciona?", "Ayuda", mensajes irrelevantes

Entidades a extraer:
- phone_number: Número de teléfono si lo mencionó (normalizar a formato con código de área, ej: "11-4567-8900")
- service_type: Tipo de servicio (dentista, peluquería, mecánico, médico, veterinario, etc.)
- location: Barrio o zona mencionada
- date_preference: Cuándo quiere el turno (hoy, mañana, esta semana, lunes, martes, etc.)
- time_preference: Horario preferido (mañana, tarde, noche, 15:00, etc.)
- specific_request: Cualquier pedido específico (consulta de rutina, limpieza, corte y barba, etc.)
- selected_option: Si el usuario está eligiendo una opción previamente presentada (1, 2, 3, etc.)

Reglas:
- Si el mensaje es solo un número (1, 2, 3) o "el primero", "el segundo", la intención es "confirm" con selected_option
- Si dice "sí", "dale", "ok" sin contexto, la intención es "confirm" sin selected_option
- Si el mensaje es ambiguo, preferir "help"
- Si dice "buscar" o "ver opciones" sin pedir que llame, es "search_only"
- Si dice "llamar", "agendar", "pedir turno", es "search_and_call"
- phone_number solo si es un número de teléfono real (al menos 7 dígitos)

Respondé SOLO con el JSON, sin texto adicional."""
```

### Función de parsing

```python
from openai import AsyncOpenAI

openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

async def parse_message(user_message: str) -> ParsedMessage:
    """Parsear un mensaje de WhatsApp y extraer intención + entidades."""

    response = await openai_client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": NLU_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        response_format=ParsedMessage,
        temperature=0.1,  # Bajo para consistencia
    )

    return response.choices[0].message.parsed
```

### Alternativa sin Structured Outputs (más compatible)

Si `beta.chat.completions.parse` da problemas, usar `response_format={"type": "json_object"}`:

```python
import json

async def parse_message_fallback(user_message: str) -> ParsedMessage:
    """Fallback: usar json_object mode en vez de structured outputs."""

    response = await openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": NLU_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
    )

    raw = json.loads(response.choices[0].message.content)
    return ParsedMessage(**raw)
```

---

## 3. Ejemplos de Parsing

| Mensaje del usuario | Intent | Entidades |
|---------------------|--------|-----------|
| "Necesito un dentista en Palermo para mañana" | search_and_call | service_type="dentista", location="Palermo", date_preference="mañana" |
| "Llamá al 4567-8900 y pedí turno para el miércoles a la tarde" | call_number | phone_number="11-4567-8900", date_preference="miércoles", time_preference="tarde" |
| "Qué peluquerías hay en Belgrano?" | search_only | service_type="peluquería", location="Belgrano" |
| "El 1" | confirm | selected_option=1 |
| "Dale, sí" | confirm | (sin entidades) |
| "No, cancelá" | cancel | (sin entidades) |
| "Cómo funciona esto?" | help | (sin entidades) |
| "Necesito un mecánico urgente cerca de Caballito, si puede ser hoy" | search_and_call | service_type="mecánico", location="Caballito", date_preference="hoy", specific_request="urgente" |

---

## 4. Whisper — Transcribir Audios de WhatsApp

### El flujo

1. Usuario manda audio por WhatsApp
2. Twilio lo sube y te da la URL (formato OGG/Opus)
3. Descargás el audio (con auth de Twilio)
4. Lo mandás a Whisper API
5. Whisper devuelve texto
6. Procesás el texto igual que un mensaje de texto

### Modelos disponibles

| Modelo | Velocidad | Calidad | Precio |
|--------|-----------|---------|--------|
| `whisper-1` | Rápido | Muy buena | $0.006/min |
| `gpt-4o-mini-transcribe` | Rápido | Excelente | $0.003/min |
| `gpt-4o-transcribe` | Medio | La mejor | $0.006/min |

Para el hackathon: **whisper-1** o **gpt-4o-mini-transcribe**.

### Código

```python
import io

async def transcribe_audio(audio_bytes: bytes, filename: str = "audio.ogg") -> str:
    """Transcribir audio usando Whisper API.

    audio_bytes: bytes del archivo de audio
    filename: nombre con extensión (importante para que Whisper detecte el formato)
    """
    # Crear un file-like object
    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = filename  # Whisper necesita la extensión

    response = await openai_client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file,
        language="es",  # Forzar español para mejor accuracy
    )

    return response.text
```

### Formatos soportados

Whisper acepta: `mp3`, `mp4`, `mpeg`, `mpga`, `m4a`, `wav`, `webm`, `ogg`

WhatsApp envía audio en formato OGG — que está soportado directamente.

### Límite de tamaño

- Máximo **25 MB** por archivo
- Los audios de WhatsApp típicos (1-2 minutos) pesan ~200KB-1MB, así que no hay problema

---

## 5. Flujo Completo: Audio de WhatsApp → Texto → NLU

```python
async def process_whatsapp_audio(
    media_url: str,
    http_client: httpx.AsyncClient,
) -> ParsedMessage:
    """Descargar audio de WhatsApp, transcribir, y parsear."""

    # 1. Descargar el audio de Twilio
    audio_bytes = await download_whatsapp_audio(media_url, http_client)

    # 2. Transcribir con Whisper
    text = await transcribe_audio(audio_bytes, "audio.ogg")

    # 3. Parsear con NLU
    parsed = await parse_message(text)

    return parsed
```

---

## 6. Manejo de Errores

```python
from openai import APIError, APITimeoutError

async def safe_parse_message(user_message: str) -> ParsedMessage:
    """Parse con manejo de errores."""
    try:
        return await parse_message(user_message)
    except APITimeoutError:
        # OpenAI tardó demasiado
        return ParsedMessage(intent=IntentType.HELP)
    except APIError as e:
        print(f"OpenAI API error: {e}")
        return ParsedMessage(intent=IntentType.HELP)
    except Exception as e:
        print(f"Error parsing message: {e}")
        return ParsedMessage(intent=IntentType.HELP)
```

Si falla, default a "help" y pedirle al usuario que reformule.

---

## 7. Links de referencia

- Structured Outputs: https://platform.openai.com/docs/guides/structured-outputs
- Chat Completions API: https://platform.openai.com/docs/api-reference/chat
- Speech to Text: https://platform.openai.com/docs/guides/speech-to-text
- Audio API Reference: https://platform.openai.com/docs/api-reference/audio
- Python SDK: https://github.com/openai/openai-python
- GPT-4o-mini pricing: https://openai.com/api/pricing
