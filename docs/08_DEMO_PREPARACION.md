# Demo y Preparación — Guía para el Hackathon

## 1. Checklist Pre-Hackathon

### Cuentas y API Keys (hacer ANTES del hackathon)

- [ ] **Twilio**: Cuenta creada, Account SID y Auth Token anotados
- [ ] **Twilio WhatsApp Sandbox**: Activado, código de join anotado
- [ ] **Twilio Phone Number**: Comprado (~$1 USD) y anotado
- [ ] **ElevenLabs**: Cuenta creada, API Key anotada
- [ ] **ElevenLabs Agente**: Agente creado en dashboard (aunque sea básico)
- [ ] **ElevenLabs Twilio Import**: Número de Twilio importado en ElevenLabs
- [ ] **OpenAI**: Cuenta creada, API Key anotada, créditos verificados
- [ ] **Google Cloud**: Proyecto creado, Places API habilitada, API Key creada
- [ ] **ngrok**: Cuenta creada, auth token configurado, dominio estable obtenido

### Verificaciones (hacer ANTES del hackathon)

- [ ] Mandar mensaje al sandbox de WhatsApp → recibir respuesta
- [ ] Hacer una llamada de prueba con Twilio Voice → suena el teléfono
- [ ] Hacer una llamada con GPT-4o-mini → responde JSON válido
- [ ] Buscar en Google Places API → devuelve resultados con teléfonos
- [ ] Hablar con un agente de ElevenLabs en el playground → responde en español
- [ ] Todos los teléfonos del equipo registrados en el sandbox de WhatsApp

### Archivos Listos (hacer ANTES del hackathon)

- [ ] `.env` con todas las variables configuradas
- [ ] `demo_providers.json` con datos de prueba
- [ ] `requirements.txt` completo
- [ ] Estructura de carpetas creada

---

## 2. Datos de Prueba

### demo_providers.json

```json
[
    {
        "id": "demo_dentista_1",
        "name": "Consultorio Dental Dr. García",
        "address": "Av. Santa Fe 1234, Palermo, Buenos Aires",
        "phone": "+5411XXXXXXXX",
        "rating": 4.8,
        "rating_count": 156,
        "service": "dentista"
    },
    {
        "id": "demo_dentista_2",
        "name": "Odontología Integral Dra. López",
        "address": "Av. Córdoba 5678, Palermo, Buenos Aires",
        "phone": "+5411XXXXXXXX",
        "rating": 4.6,
        "rating_count": 89,
        "service": "dentista"
    },
    {
        "id": "demo_peluqueria_1",
        "name": "Barbería Don Carlos",
        "address": "Honduras 4500, Palermo, Buenos Aires",
        "phone": "+5411XXXXXXXX",
        "rating": 4.9,
        "rating_count": 312,
        "service": "peluquería"
    },
    {
        "id": "demo_mecanico_1",
        "name": "Taller Mecánico Rápido",
        "address": "Av. Juan B. Justo 2200, Palermo, Buenos Aires",
        "phone": "+5411XXXXXXXX",
        "rating": 4.3,
        "rating_count": 67,
        "service": "mecánico"
    }
]
```

**IMPORTANTE**: Reemplazar los `+5411XXXXXXXX` con números reales para el demo. Opciones:
1. Números de teléfono de los integrantes del equipo (uno atiende como recepcionista)
2. Números de un segundo Twilio number que simula la recepcionista
3. Números reales de negocios (riesgoso para demo en vivo)

---

## 3. Recepcionista Simulada

### Opción A: Persona del equipo atiende

La opción más confiable para el demo. Una persona del equipo:
1. Recibe la llamada en su celular
2. Actúa como recepcionista
3. Ofrece horarios, responde preguntas
4. Simula un booking exitoso

**Script para la recepcionista simulada:**
```
[Suena el teléfono]
"Hola, Consultorio Dr. García, buenas tardes."
[El agente pide turno]
"Sí, claro. Para esta semana tenemos disponible el miércoles a las 15:00 o el jueves a las 10:00. ¿Cuál le conviene?"
[El agente elige una]
"Perfecto, le agendo para el [día] a las [hora] con el Dr. García. Le pedimos que llegue 10 minutos antes con DNI. ¿Algo más?"
[El agente agradece]
"De nada, que tenga buen día."
```

### Opción B: Segundo agente de ElevenLabs como recepcionista

Crear un segundo agente en ElevenLabs que actúe como recepcionista:

**System prompt del agente recepcionista:**
```
Sos la recepcionista del Consultorio Dental Dr. García.
Atendé las llamadas de forma profesional y amable.
Tenés los siguientes turnos disponibles esta semana:
- Miércoles 15:00
- Jueves 10:00
- Viernes 11:30
Cuando alguien pide turno, ofrecé las opciones disponibles.
Cuando confirmen, pediles que lleguen 10 minutos antes con DNI.
```

Usar el número de Twilio para este segundo agente, y llamar a ese número.

### Opción C: IVR básico con Twilio

Crear un webhook que responda con TwiML simulando una recepcionista:
```python
@router.post("/demo/receptionist")
async def demo_receptionist(request: Request) -> Response:
    twiml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Mia" language="es-ES">
        Hola, Consultorio Dr. García, buenas tardes. ¿En qué puedo ayudarle?
    </Say>
    <Gather input="speech" action="/demo/receptionist/respond" method="POST"
            speechTimeout="3" language="es-AR">
    </Gather>
</Response>"""
    return Response(content=twiml, media_type="application/xml")
```

---

## 4. Guion de Demo en Vivo

### Preparar antes del demo

1. Server corriendo (`python run.py`)
2. ngrok corriendo (`ngrok http 8000`)
3. Teléfono con WhatsApp listo en pantalla
4. Consola del servidor visible para mostrar logs
5. Si usan recepcionista humana: segunda persona lista para atender

### Secuencia del Demo (5 minutos)

**[0:00 - 0:30] El Problema**
"Todos conocemos la frustración de querer agendar un turno por teléfono. Llamás, esperás, no hay turno, llamás a otro... 20 minutos para algo que debería ser instantáneo."

**[0:30 - 1:00] La Solución**
"Vocero resuelve esto. Le mandás un mensaje por WhatsApp, y Vocero llama por vos."
*Mostrar el celular con WhatsApp abierto*

**[1:00 - 3:30] Demo en Vivo**

Mensaje 1 (búsqueda):
```
Necesito un dentista en Palermo para esta semana
```
*Esperar respuesta con opciones*

Mensaje 2 (selección):
```
El 1
```
*Esperar confirmación y que empiece la llamada*

*Mostrar en la consola los logs de la llamada en tiempo real*
*Mostrar las tool calls: validate_slot, report_result*

*Esperar el mensaje de WhatsApp con el resultado*

**[3:30 - 4:00] Arquitectura (slide)**
"Vocero usa ElevenLabs Conversational AI con Agentic Functions para tomar decisiones durante la llamada. El agente no sigue un script — negocia activamente."

**[4:00 - 4:30] Impacto**
"Cualquier persona en el mundo con WhatsApp puede usar Vocero. Sin app, sin cuenta, sin fricción."

**[4:30 - 5:00] Futuro**
"Con el Batch Calling de ElevenLabs, Vocero puede llamar a 15 proveedores en paralelo y encontrar el mejor turno en segundos."

---

## 5. Slides (3-5 slides)

### Slide 1: El Problema
- Título: "El último kilómetro sin automatizar"
- Bullet: Agendar un turno por teléfono = 20-30 min
- Bullet: Llamar, esperar, negociar, repetir

### Slide 2: Vocero
- Título: "Mandá un mensaje. Vocero llama por vos."
- Screenshot de WhatsApp con la conversación
- Logos: WhatsApp + ElevenLabs + Twilio

### Slide 3: Demo (pantalla del celular)

### Slide 4: Arquitectura
- Diagrama simple:
  WhatsApp → NLU → Places → ElevenLabs Agent → Teléfono
- Destacar: Agentic Functions (validate_slot, report_result)

### Slide 5: Impacto y Futuro
- "Cero fricción: WhatsApp como interfaz universal"
- "Paralelización: Llamar a 15 lugares a la vez"
- "El turno perfecto en segundos, no minutos"

---

## 6. Video de Backup

**Grabar un video de 3 minutos** con el flujo completo funcionando, por si la demo en vivo falla:

1. Grabar la pantalla del celular mostrando WhatsApp
2. Grabar la pantalla de la computadora mostrando los logs
3. Combinar ambas tomas
4. Tener el video listo en el celular/laptop para mostrar

### Cómo grabar

- **Celular**: Usar la grabación de pantalla nativa
- **Computadora**: OBS Studio o grabación de pantalla nativa
- **Combinar**: ScreenFlow, iMovie, o simplemente mostrar las dos pantallas

---

## 7. Contingencias

| Problema | Solución |
|----------|----------|
| ngrok se cae | Reiniciar ngrok. Si usan dominio estable, no hay que reconfigurar Twilio |
| WhatsApp sandbox no responde | Verificar que el join no expiró. Re-enviar "join <código>" |
| La llamada no conecta | Mostrar video de backup |
| Latencia alta en la respuesta | Los mensajes de "procesando..." cubrirán la espera |
| Google Places no devuelve resultados | Usar demo_providers.json como fallback |
| ElevenLabs agente no responde bien | Usar el segundo agente/recepcionista simulada para controlar el resultado |
| El jurado quiere probar | Tener instrucciones claras: "Mandá 'join xxx' al +14155238886 y después cualquier mensaje" |

---

## 8. Orden de Desarrollo (recordatorio)

| Hora | Qué | Definición de "listo" |
|------|-----|----------------------|
| 0-1 | Setup + PROBAR LLAMADA | Una llamada de ElevenLabs funciona |
| 1-4 | WhatsApp + NLU | Mandar "dentista en palermo" y recibir respuesta parseada |
| 4-7 | Google Places | Recibir opciones reales con teléfonos por WhatsApp |
| 7-12 | Agente de voz + Tools | Llamada completa con validate_slot y report_result |
| 12-16 | Flujo completo | WhatsApp → buscar → llamar → resultado por WhatsApp |
| 16-20 | Pulido + stretch | Audio, modo enjambre, mejor UX |
| 20-24 | Demo + presentación | Todo ensayado, video grabado, slides listas |

---

## 9. Comandos Rápidos

```bash
# Arrancar todo
cd /Users/mauro/Desktop/proyectos/vocero
source venv/bin/activate
python run.py &
ngrok http 8000 --domain=tu-subdominio.ngrok-free.app &

# Ver logs
# (los logs aparecen en la terminal del server)

# Reiniciar server
pkill -f "python run.py" && python run.py &

# Probar health
curl https://tu-subdominio.ngrok-free.app/health

# Ver requests de ngrok
open http://127.0.0.1:4040
```
