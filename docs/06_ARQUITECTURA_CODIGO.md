# Arquitectura y Código — Estructura del Proyecto

## 1. Estructura de Archivos

```
vocero/
├── docs/                          # Documentación (esta carpeta)
│   ├── 00_INDICE.md
│   ├── 01_ELEVENLABS_GUIA.md
│   ├── ...
│   └── 08_DEMO_PREPARACION.md
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI entry point
│   ├── config.py                  # Variables de entorno (pydantic-settings)
│   ├── state.py                   # Estado en memoria
│   ├── orchestrator.py            # Lógica principal del flujo
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── whatsapp.py            # Webhook de WhatsApp (Twilio)
│   │   ├── voice.py               # Webhook de Twilio Voice + status
│   │   └── tools.py               # Endpoints para Agentic Functions de ElevenLabs
│   ├── services/
│   │   ├── __init__.py
│   │   ├── nlu.py                 # NLU con OpenAI GPT-4o-mini
│   │   ├── places.py              # Google Places API
│   │   ├── voice.py               # ElevenLabs llamadas salientes
│   │   ├── whatsapp.py            # Enviar mensajes por WhatsApp
│   │   └── transcription.py       # Whisper transcripción de audio
│   └── models/
│       ├── __init__.py
│       └── schemas.py             # Pydantic models
├── data/
│   └── demo_providers.json        # Datos de prueba para el demo
├── .env                           # Variables de entorno (NO committear)
├── .env.example                   # Template de variables
├── .gitignore
├── requirements.txt
├── run.py                         # Script para arrancar el servidor
└── VOCERO_Plan_Integral.md        # Plan original
```

---

## 2. Dependencias

### requirements.txt

```
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
httpx>=0.27.0
websockets>=13.0
python-dotenv>=1.0.0
python-multipart>=0.0.12
pydantic>=2.9.0
pydantic-settings>=2.5.0
twilio>=9.3.0
openai>=1.50.0
elevenlabs>=1.0.0
```

### Instalar

```bash
cd /Users/mauro/Desktop/proyectos/vocero
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## 3. Configuración

### .env.example

```bash
# === Server ===
PORT=8000
DEBUG=true
BASE_URL=https://tu-subdominio.ngrok-free.app

# === Twilio ===
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=tu_auth_token
TWILIO_WHATSAPP_NUMBER=+14155238886
TWILIO_PHONE_NUMBER=+1xxxxxxxxxx

# === ElevenLabs ===
ELEVENLABS_API_KEY=tu_api_key
ELEVENLABS_AGENT_ID=agent_xxxxxxxxxxxx
ELEVENLABS_PHONE_NUMBER_ID=phnum_xxxxxxxxxxxx

# === OpenAI ===
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx

# === Google Places ===
GOOGLE_PLACES_API_KEY=AIzaXXXXXXXXXXXXXXXXXXXXXXXXXX
```

### app/config.py

```python
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Server
    port: int = 8000
    debug: bool = False
    base_url: str = ""

    # Twilio
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_whatsapp_number: str = ""
    twilio_phone_number: str = ""

    # ElevenLabs
    elevenlabs_api_key: str = ""
    elevenlabs_agent_id: str = ""
    elevenlabs_phone_number_id: str = ""

    # OpenAI
    openai_api_key: str = ""

    # Google Places
    google_places_api_key: str = ""

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

---

## 4. Entry Point

### app/main.py

```python
from contextlib import asynccontextmanager
import httpx
from fastapi import FastAPI
from dotenv import load_dotenv

load_dotenv()

from app.config import get_settings
from app.routers import whatsapp, voice, tools


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup y shutdown."""
    # Startup: crear HTTP client compartido
    app.state.http_client = httpx.AsyncClient(timeout=30.0)
    print("Vocero server started")
    yield
    # Shutdown
    await app.state.http_client.aclose()
    print("Vocero server stopped")


app = FastAPI(
    title="Vocero",
    version="0.1.0",
    lifespan=lifespan,
)

# Routers
app.include_router(whatsapp.router, prefix="/webhook", tags=["whatsapp"])
app.include_router(voice.router, prefix="/webhook", tags=["voice"])
app.include_router(tools.router, prefix="/api/tools", tags=["tools"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "vocero"}
```

### run.py

```python
import uvicorn
from app.config import get_settings

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=settings.debug,
    )
```

---

## 5. Estado en Memoria

### app/state.py

```python
import asyncio
from typing import Any
from app.models.schemas import ConversationState

# Estado de conversaciones: phone_number -> ConversationState
conversations: dict[str, ConversationState] = {}

# Lock para operaciones atómicas
state_lock = asyncio.Lock()


async def get_conversation(phone: str) -> ConversationState:
    """Obtener o crear el estado de conversación para un número."""
    async with state_lock:
        if phone not in conversations:
            conversations[phone] = ConversationState(phone=phone)
        return conversations[phone]


def clear_conversation(phone: str) -> None:
    """Limpiar el estado de una conversación."""
    conversations.pop(phone, None)
```

---

## 6. Modelos de Datos

### app/models/schemas.py

```python
from pydantic import BaseModel
from typing import Optional
from enum import Enum


class IntentType(str, Enum):
    CALL_NUMBER = "call_number"
    SEARCH_AND_CALL = "search_and_call"
    SEARCH_ONLY = "search_only"
    CONFIRM = "confirm"
    CANCEL = "cancel"
    HELP = "help"


class ParsedMessage(BaseModel):
    intent: IntentType
    phone_number: Optional[str] = None
    service_type: Optional[str] = None
    location: Optional[str] = None
    date_preference: Optional[str] = None
    time_preference: Optional[str] = None
    specific_request: Optional[str] = None
    selected_option: Optional[int] = None


class ConversationStatus(str, Enum):
    IDLE = "idle"
    AWAITING_SELECTION = "awaiting_selection"
    CALLING = "calling"
    AWAITING_CONFIRMATION = "awaiting_confirmation"


class CallResult(BaseModel):
    status: str  # booked, no_availability, callback_needed, wrong_number, no_answer, failed
    date: Optional[str] = None
    time: Optional[str] = None
    professional_name: Optional[str] = None
    notes: Optional[str] = None
    instructions: Optional[str] = None


class PlaceInfo(BaseModel):
    id: str
    name: str
    address: str
    phone: Optional[str] = None
    rating: Optional[float] = None
    rating_count: Optional[int] = None


class ConversationState(BaseModel):
    phone: str
    status: ConversationStatus = ConversationStatus.IDLE
    search_results: list[PlaceInfo] = []
    pending_entities: Optional[ParsedMessage] = None
    current_call_id: Optional[str] = None
    call_results: list[CallResult] = []
```

---

## 7. Routers Esqueleto

### app/routers/whatsapp.py

```python
from fastapi import APIRouter, Request, Response
from app.orchestrator import process_incoming_message

router = APIRouter()


@router.post("/whatsapp")
async def whatsapp_webhook(request: Request) -> Response:
    form_data = await request.form()
    from_number = form_data.get("From", "").replace("whatsapp:", "")
    body = form_data.get("Body", "")
    num_media = int(form_data.get("NumMedia", "0"))
    media_url = form_data.get("MediaUrl0") if num_media > 0 else None
    media_type = form_data.get("MediaContentType0") if num_media > 0 else None

    # Procesar asincrónicamente (no bloquear la respuesta a Twilio)
    import asyncio
    asyncio.create_task(
        process_incoming_message(from_number, body, media_url, media_type, request.app)
    )

    # Respuesta vacía a Twilio
    twiml = '<?xml version="1.0" encoding="UTF-8"?><Response></Response>'
    return Response(content=twiml, media_type="application/xml")
```

### app/routers/tools.py

```python
from fastapi import APIRouter, Request
from app.models.schemas import CallResult

router = APIRouter()


@router.post("/validate_slot")
async def validate_slot(request: Request) -> dict:
    """Server tool de ElevenLabs: validar un horario propuesto."""
    data = await request.json()
    date = data.get("date", "")
    time = data.get("time", "")

    # Validar contra las preferencias del usuario
    # (buscar el call_id en el estado, verificar preferencias)

    return {"valid": True, "message": "El horario es aceptable para el usuario."}


@router.post("/report_result")
async def report_result(request: Request) -> dict:
    """Server tool de ElevenLabs: reportar resultado de la llamada."""
    data = await request.json()

    result = CallResult(
        status=data.get("status", "failed"),
        date=data.get("date"),
        time=data.get("time"),
        professional_name=data.get("professional_name"),
        notes=data.get("notes"),
        instructions=data.get("instructions"),
    )

    # Guardar resultado y notificar al usuario por WhatsApp
    # await notify_user_call_result(call_id, result)

    return {"success": True, "message": "Resultado recibido."}
```

### app/routers/voice.py

```python
from fastapi import APIRouter, Request, Response

router = APIRouter()


@router.post("/voice/status")
async def voice_status(request: Request) -> Response:
    """Callback de estado de llamada de Twilio."""
    form_data = await request.form()
    call_sid = form_data.get("CallSid", "")
    call_status = form_data.get("CallStatus", "")

    print(f"Call {call_sid} status: {call_status}")

    if call_status in ("busy", "no-answer", "failed"):
        # Notificar al usuario que no se pudo conectar
        pass

    return Response(content="OK", media_type="text/plain")
```

---

## 8. ngrok Setup

### Instalar

```bash
brew install ngrok
```

### Configurar

```bash
ngrok config add-authtoken TU_NGROK_TOKEN
```

### Ejecutar

```bash
# Con dominio estable (gratis, recomendado)
ngrok http 8000 --domain=tu-subdominio.ngrok-free.app

# Sin dominio (cambia cada vez)
ngrok http 8000
```

### Configurar webhooks

Una vez que ngrok está corriendo:
1. Copiar la URL HTTPS (ej: `https://tu-subdominio.ngrok-free.app`)
2. Actualizar `BASE_URL` en `.env`
3. En Twilio Console:
   - WhatsApp Sandbox → "When a message comes in": `https://tu-subdominio.ngrok-free.app/webhook/whatsapp` (POST)
   - Phone Number → Voice "A call comes in": `https://tu-subdominio.ngrok-free.app/webhook/voice/outbound` (POST)

### Dashboard de ngrok

Inspeccionar requests en: http://127.0.0.1:4040

---

## 9. Arrancar Todo

```bash
# Terminal 1: servidor
cd /Users/mauro/Desktop/proyectos/vocero
source venv/bin/activate
python run.py

# Terminal 2: ngrok
ngrok http 8000 --domain=tu-subdominio.ngrok-free.app
```

Verificar:
- `http://localhost:8000/health` → `{"status": "ok", "service": "vocero"}`
- `https://tu-subdominio.ngrok-free.app/health` → mismo resultado

---

## 10. Diagrama de Flujo Resumido

```
Usuario (WhatsApp)
    │
    ▼
Twilio Messaging ──POST──▶ /webhook/whatsapp (FastAPI)
                                │
                                ▼
                           Orchestrator
                           ┌────┴────┐
                           │         │
                    NLU (OpenAI)   Places (Google)
                           │         │
                           └────┬────┘
                                │
                                ▼
                      ElevenLabs Outbound Call API
                                │
                                ▼
                    Twilio Voice → Teléfono del negocio
                                │
                    ElevenLabs Agent ← → Recepcionista
                                │
                     Tool calls: validate_slot, report_result
                                │
                                ▼
                   POST a /api/tools/* (FastAPI)
                                │
                                ▼
                    Enviar resultado por WhatsApp
```
