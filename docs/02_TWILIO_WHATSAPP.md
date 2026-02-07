# Twilio WhatsApp — Guía Completa

## 1. WhatsApp Sandbox

El sandbox de Twilio permite probar WhatsApp sin necesidad de aprobación de Meta.

### Setup del Sandbox

1. Ir a https://console.twilio.com/us1/develop/sms/try-it-out/whatsapp-learn
2. Twilio asigna un número de sandbox (ej: `+14155238886`)
3. Cada usuario debe mandar un mensaje de "join" para activarse:
   - Mandar `join <código>` al número del sandbox por WhatsApp
   - Ejemplo: `join funny-penguin`
4. Máximo **3 usuarios registrados** por defecto

### Limitaciones del Sandbox

- Solo funciona con números que hayan mandado el mensaje de "join"
- Los mensajes del sandbox tienen un prefijo de Twilio
- El join expira después de 72 horas de inactividad
- No se puede personalizar el número (es compartido)

### Configurar Webhook

En la consola del sandbox:
1. Ir a "Sandbox Configuration" (o "When a message comes in")
2. URL: `https://TU_NGROK_URL/webhook/whatsapp`
3. Method: **POST**

---

## 2. Recibir Mensajes (Webhook)

Cuando un usuario manda un mensaje por WhatsApp, Twilio hace un **POST** a tu webhook con datos en formato `application/x-www-form-urlencoded`.

### Campos del webhook (los más importantes)

| Campo | Ejemplo | Descripción |
|-------|---------|-------------|
| `MessageSid` | `SMxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` | ID único del mensaje |
| `From` | `whatsapp:+5491155556666` | Número del remitente (con prefijo "whatsapp:") |
| `To` | `whatsapp:+14155238886` | Número del sandbox |
| `Body` | `Necesito un dentista en Palermo` | Texto del mensaje |
| `NumMedia` | `1` | Cantidad de archivos adjuntos |
| `MediaUrl0` | `https://api.twilio.com/...` | URL del primer archivo adjunto |
| `MediaContentType0` | `audio/ogg` | MIME type del archivo adjunto |

### Código FastAPI para recibir mensajes

```python
from fastapi import APIRouter, Request, Response

router = APIRouter()

@router.post("/whatsapp")
async def whatsapp_webhook(request: Request) -> Response:
    form_data = await request.form()

    from_number = form_data.get("From", "")       # "whatsapp:+5491155556666"
    body = form_data.get("Body", "")               # texto del mensaje
    num_media = int(form_data.get("NumMedia", "0"))

    # Extraer el número limpio (sin "whatsapp:")
    phone = from_number.replace("whatsapp:", "")

    # Si hay audio adjunto
    if num_media > 0:
        media_url = form_data.get("MediaUrl0", "")
        media_type = form_data.get("MediaContentType0", "")
        # Si es audio, transcribir con Whisper (ver 05_OPENAI_NLU.md)

    # Procesar el mensaje (llamar al orquestador)
    # response_text = await orchestrator.process(phone, body)

    # Responder con TwiML vacío (respondemos via API, no via TwiML)
    twiml = '<?xml version="1.0" encoding="UTF-8"?><Response></Response>'
    return Response(content=twiml, media_type="application/xml")
```

### Por qué responder TwiML vacío

Hay dos formas de responder al usuario:
1. **Via TwiML** (en la respuesta del webhook): Rápido pero limitado
2. **Via API** (llamada separada): Más flexible, permite responder asincrónicamente

Para Vocero usamos la **API** porque necesitamos responder en momentos diferentes (cuando termina el NLU, cuando termina la búsqueda, cuando termina la llamada). El webhook solo devuelve un TwiML vacío.

---

## 3. Enviar Mensajes (API)

### Con la librería de Twilio

```python
from twilio.rest import Client

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

def send_whatsapp(to_number: str, body: str):
    """Enviar un mensaje de WhatsApp.

    to_number: número con formato internacional, ej: "+5491155556666"
    """
    message = client.messages.create(
        body=body,
        from_=f"whatsapp:{TWILIO_WHATSAPP_NUMBER}",  # el número del sandbox
        to=f"whatsapp:{to_number}"
    )
    return message.sid
```

### Enviar mensajes con formato

WhatsApp soporta formato básico:
- **Negrita**: `*texto*`
- **Cursiva**: `_texto_`
- **Tachado**: `~texto~`
- **Monospace**: `` ```texto``` ``

Ejemplo de mensaje formateado:
```python
msg = """*Vocero encontró estas opciones:*

1. _Dr. García_ - ⭐ 4.8
   📍 Av. Santa Fe 1234, Palermo
   📞 11-4567-8900

2. _Dra. López_ - ⭐ 4.6
   📍 Av. Córdoba 5678, Palermo
   📞 11-9876-5432

Respondé con el número de la opción que querés."""
```

---

## 4. Manejar Audio de WhatsApp

Cuando el usuario manda un audio, Twilio lo sube a sus servidores y te da la URL.

### Formato del audio

- WhatsApp envía audio en formato **OGG/Opus** (`audio/ogg`)
- La URL del audio requiere autenticación de Twilio para descargarlo

### Descargar el audio

```python
import httpx
from base64 import b64encode

async def download_whatsapp_audio(media_url: str, http_client: httpx.AsyncClient) -> bytes:
    """Descargar audio de WhatsApp desde Twilio.

    La URL requiere autenticación con las credenciales de Twilio.
    """
    auth_string = b64encode(
        f"{TWILIO_ACCOUNT_SID}:{TWILIO_AUTH_TOKEN}".encode()
    ).decode()

    response = await http_client.get(
        media_url,
        headers={"Authorization": f"Basic {auth_string}"},
        follow_redirects=True
    )
    response.raise_for_status()
    return response.content  # bytes del archivo de audio
```

Después de descargar, transcribir con Whisper (ver **05_OPENAI_NLU.md**).

---

## 5. Mensajes de Estado Intermedio

Para mejorar la UX, enviar mensajes de "procesando" inmediatamente:

```python
async def handle_message(phone: str, body: str):
    # 1. Acusar recibo inmediatamente
    send_whatsapp(phone, "🔍 Procesando tu mensaje...")

    # 2. Procesar con NLU
    intent = await nlu.parse(body)

    # 3. Según la intención
    if intent.type == "search_and_call":
        send_whatsapp(phone, "🔎 Buscando opciones cerca tuyo...")
        results = await places.search(intent.service_type, intent.location)
        send_whatsapp(phone, format_results(results))

    elif intent.type == "call_number":
        send_whatsapp(phone, "📞 Llamando... Te aviso cuando termine.")
        result = await voice.call(intent.phone_number, intent)
        send_whatsapp(phone, format_call_result(result))
```

---

## 6. Checklist de Setup

- [ ] Crear cuenta en Twilio (https://www.twilio.com/try-twilio)
- [ ] Obtener Account SID y Auth Token
- [ ] Activar el WhatsApp Sandbox
- [ ] Enviar "join <código>" desde todos los teléfonos del equipo
- [ ] Configurar el webhook URL (apuntar a ngrok)
- [ ] Comprar un número de teléfono para llamadas de voz (~$1 USD)
- [ ] Verificar que el sandbox responde (mandar un mensaje de prueba)

## 7. Links de referencia

- Sandbox: https://www.twilio.com/docs/whatsapp/sandbox
- Quickstart: https://www.twilio.com/docs/whatsapp/quickstart
- Webhook Request format: https://www.twilio.com/docs/messaging/guides/webhook-request
- Messaging API: https://www.twilio.com/docs/messaging/api
- FastAPI + Twilio tutorial: https://www.twilio.com/en-us/blog/build-secure-twilio-webhook-python-fastapi
- WhatsApp + ChatGPT tutorial: https://www.twilio.com/en-us/blog/ai-chatbot-whatsapp-python-twilio-openai
