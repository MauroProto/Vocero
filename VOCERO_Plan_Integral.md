# VOCERO — Plan Integral del Proyecto

**"Mandá un mensaje. Vocero llama por vos."**

---

# PARTE 1: CONTEXTO DEL HACKATHON Y CHALLENGE

## Sobre el Hackathon

- **Duración:** 24 horas
- **Equipo:** 2-3 personas
- **Nombre del proyecto:** Vocero
- **Challenge elegido:** CallPilot — Agentic Voice AI for Autonomous Appointment Scheduling
- **Sponsor del track:** ElevenLabs
- **Requerimiento obligatorio:** Usar tecnología de ElevenLabs (Conversational AI SDK, Agentic Functions)

## El Challenge: CallPilot by ElevenLabs

### El Problema

Agendar un turno por teléfono sigue siendo una de las micro-tareas más consumidoras de tiempo en la vida cotidiana. Llamás, esperás en espera, negociás un horario, te das cuenta de que no encaja en tu calendario, llamás al siguiente lugar, repetís. Para un solo turno, esto puede consumir fácilmente 20-30 minutos.

Ningún humano puede paralelizar eficientemente 15 llamadas telefónicas a la vez — pero un agente de voz de IA sí puede.

### Qué Piden Construir

Un agente de voz de IA agéntico impulsado por ElevenLabs que autónomamente:

- Llame a proveedores de servicios
- Negocie horarios de turnos en conversación natural
- Seleccione el match óptimo basado en calendario, ubicación y preferencias
- Aproveche las Funciones Agénticas de ElevenLabs (tool calling) para orquestar campañas de múltiples llamadas y tomar decisiones en tiempo real

### Criterios de Evaluación del Jurado

- **Calidad Conversacional (peso alto):** Interacción natural, manejo de interrupciones, latencia menor a 1 segundo
- **Uso de Funciones Agénticas (peso alto):** Orquestación efectiva de herramientas y toma de decisiones usando tool calling de ElevenLabs
- **Calidad del Match Óptimo:** Calidad de la recomendación final que le llega al usuario
- **Paralelización y Escalabilidad:** Manejo de llamadas concurrentes y fallos
- **Experiencia de Usuario:** Viaje fluido desde la solicitud hasta el turno reservado

---

# PARTE 2: NUESTRA PROPUESTA — VOCERO

## Concepto

Vocero es un agente de voz de IA accesible via WhatsApp que hace llamadas telefónicas por vos. El usuario manda un mensaje de WhatsApp (texto o audio), Vocero entiende qué necesita, busca opciones si hace falta, llama al negocio, negocia el turno hablando con la recepcionista en conversación natural, y reporta el resultado por WhatsApp.

## Por Qué WhatsApp

No hay app que instalar. No hay interfaz que aprender. No hay página web que visitar. WhatsApp es la interfaz y todo el mundo ya lo tiene. Es la forma más natural, accesible y universal de interactuar con un agente de IA. Para el jurado, esto demuestra impacto real: cualquier persona del planeta puede usar Vocero sin barreras de adopción.

## Flujos de Usuario

### Flujo 1: El usuario pasa un número de teléfono directamente

El usuario le manda un mensaje a Vocero diciendo algo como "Llamá al 11-4567-8900 y pedí turno para el dentista mañana a la tarde". Vocero confirma que va a llamar, hace la llamada con el agente de voz de ElevenLabs, y cuando termina le manda un resumen por WhatsApp con el resultado: si consiguió turno, para qué día y hora, con quién, y cualquier instrucción adicional (como "venir en ayunas").

### Flujo 2: El usuario pide un tipo de servicio y Vocero busca opciones

El usuario manda "Necesito un dentista cerca de Palermo para esta semana". Vocero busca en Google Places, encuentra opciones con nombre, dirección, rating y teléfono, y se las presenta por WhatsApp como una lista numerada. El usuario responde con el número de la opción que quiere (ej: "el 1") y Vocero llama a ese negocio.

### Flujo 3: Modo enjambre (stretch goal)

El usuario dice "Necesito el turno más temprano posible con cualquier dentista en Palermo". Vocero llama a los 3 mejores en paralelo, cada llamada como una instancia independiente del agente de voz, y le presenta al usuario un ranking de resultados ordenado por disponibilidad más temprana, rating y distancia.

### Flujo 4: Audio de WhatsApp (stretch goal)

El usuario manda un audio en vez de texto. Vocero lo transcribe con Whisper y lo procesa como si fuera texto. Mismo flujo, pero aún más natural para el usuario.

---

# PARTE 3: ARQUITECTURA TÉCNICA

## Visión General

El sistema tiene 5 componentes principales que se comunican entre sí:

**WhatsApp (via Twilio)** es la interfaz con el usuario. Twilio ofrece un sandbox de WhatsApp gratuito para desarrollo que no requiere aprobación de Meta. Cada vez que el usuario manda un mensaje, Twilio envía un POST a nuestro backend con el contenido del mensaje. Para responder, nuestro backend llama a la API de Twilio para enviar mensajes de vuelta.

**Backend (FastAPI en Python)** es el cerebro orquestador. Recibe los mensajes de WhatsApp, los procesa, decide qué hacer, coordina las llamadas a los demás servicios, y mantiene el estado de cada conversación en memoria.

**NLU con OpenAI (GPT-4o-mini)** es el módulo que entiende qué quiere el usuario. Toma el texto libre del mensaje y extrae información estructurada: la intención (llamar a un número, buscar un negocio, confirmar una opción, cancelar, pedir ayuda) y las entidades (tipo de servicio, ubicación, fecha preferida, horario, número de teléfono, pedidos especiales).

**Google Places API** es el buscador de negocios. Cuando el usuario pide un tipo de servicio en una zona, buscamos en Google Places, obtenemos los resultados con nombre, dirección, rating y teléfono, y se los presentamos al usuario.

**ElevenLabs Conversational AI + Twilio Voice** es el agente de voz que hace las llamadas. Twilio inicia la llamada telefónica saliente y conecta el audio bidireccional via WebSocket con ElevenLabs. El agente de ElevenLabs habla con la recepcionista en conversación natural, usando Agentic Functions (tool calling) para validar horarios, reportar resultados y consultar al usuario si necesita información adicional.

## Flujo Técnico Paso a Paso

1. El usuario manda un mensaje de WhatsApp
2. Twilio recibe el mensaje y hace un POST a nuestro webhook
3. El backend recibe el mensaje y lo manda a OpenAI para extraer intención y entidades
4. Según la intención, el backend decide el siguiente paso:
   - Si el usuario pasó un número: ir directo al paso 6
   - Si pidió un tipo de servicio: ir al paso 5
   - Si está eligiendo una opción previamente presentada: ir al paso 6
   - Si necesita ayuda: responder con instrucciones
5. El backend busca negocios en Google Places, formatea los resultados y los manda por WhatsApp al usuario. Espera su selección.
6. El backend configura el agente de voz de ElevenLabs con el contexto de la llamada (qué servicio pedir, para cuándo, pedidos especiales) y le da un system prompt detallado
7. El backend inicia una llamada saliente via Twilio Voice al número del negocio
8. Twilio conecta el audio de la llamada con ElevenLabs via WebSocket (Media Streams)
9. El agente de ElevenLabs habla con la recepcionista, negocia el turno, y usa tool calling para reportar el resultado
10. El backend recibe el resultado del agente y le manda un resumen al usuario por WhatsApp

## Stack Tecnológico

- **Interfaz de usuario:** WhatsApp via Twilio Messaging API
- **Backend / Orquestador:** Python 3.11+ con FastAPI
- **NLU (entender al usuario):** OpenAI GPT-4o-mini con respuesta en JSON estructurado
- **Búsqueda de negocios:** Google Places API (Text Search + Place Details)
- **Agente de voz:** ElevenLabs Conversational AI SDK con WebSocket
- **Tool calling del agente:** ElevenLabs Agentic Functions
- **Llamadas telefónicas:** Twilio Programmable Voice con Media Streams
- **Transcripción de audio de WhatsApp:** OpenAI Whisper API
- **Estado de conversaciones:** Diccionario en memoria (alcanza para el hackathon)
- **Exposición del backend:** ngrok para desarrollo local con webhooks

## Estructura del Proyecto

El proyecto se organiza en módulos claros:

- **Módulo WhatsApp:** Maneja la recepción de mensajes entrantes (webhook), el envío de respuestas, y el procesamiento de audios y media adjunta.
- **Módulo NLU:** Contiene el system prompt que le da a OpenAI para parsear mensajes, y la función que llama a la API y devuelve el JSON estructurado con intención y entidades.
- **Módulo Search:** Integración con Google Places API para buscar negocios por tipo y ubicación, y obtener detalles como teléfono y horarios.
- **Módulo Voice:** Configuración del agente de ElevenLabs (system prompt, voz, Agentic Functions), inicio de llamadas via Twilio Voice, y manejo del WebSocket bidireccional entre Twilio y ElevenLabs.
- **Módulo Orchestrator:** La lógica principal del flujo. Recibe mensajes, consulta el NLU, decide qué hacer, coordina búsquedas y llamadas, y reporta resultados.
- **Módulo Models:** Las estructuras de datos para conversaciones, turnos y proveedores.

---

# PARTE 4: AGENTIC FUNCTIONS (TOOL CALLING)

Este es el corazón de lo que evalúa ElevenLabs. Las Agentic Functions son herramientas que el agente de voz puede invocar durante la llamada telefónica. Funcionan igual que el tool calling de OpenAI pero dentro de una conversación de voz en tiempo real.

## Herramientas del Agente

### validate_slot

Cuando la recepcionista le ofrece un horario al agente, este invoca validate_slot para verificar si ese horario es aceptable según las preferencias del usuario. Recibe fecha y hora propuestas y devuelve si es válido o no. Esto le permite al agente tomar decisiones informadas sin inventar nada.

### report_result

Cuando la llamada termina (exitosamente o no), el agente invoca report_result para informar al backend qué pasó. Incluye el estado (turno agendado, sin disponibilidad, necesita callback, número equivocado, no contestaron, falló), y si se agendó un turno, los datos completos: fecha, hora, nombre del profesional, notas e instrucciones. El backend toma esta información y la manda por WhatsApp al usuario.

### ask_user

Si durante la llamada la recepcionista pide información que el agente no tiene (ej: número de obra social, nombre completo del paciente), el agente puede invocar ask_user para consultar al usuario via WhatsApp. Esto es un stretch goal porque requiere manejar la espera en la llamada telefónica, pero demuestra un nivel de sofisticación muy alto para el jurado.

## System Prompt del Agente de Voz

El agente recibe un prompt detallado con el contexto de la llamada: qué servicio necesita, para cuándo, preferencias del usuario, y pedidos especiales. Las instrucciones le dicen que salude amablemente, pida el turno, escuche las opciones, use validate_slot para verificar, confirme si es aceptable, pida los datos del turno (día, hora, instrucciones), agradezca, y use report_result para informar al backend. El estilo es español argentino, natural y amable. Nunca inventa información y si no entiende algo, pide que lo repitan.

---

# PARTE 5: MANEJO DE CONVERSACIÓN Y ESTADO

## Estado de Cada Conversación

Cada usuario (identificado por su número de WhatsApp) tiene un estado de conversación que incluye:

- **status:** En qué momento del flujo está (inactivo, esperando selección de opción, llamando, esperando confirmación)
- **search_results:** Los resultados de la búsqueda de Google Places, si los hay
- **pending_entities:** Las entidades extraídas del NLU que todavía no se usaron (tipo de servicio, fecha, etc.)
- **current_call_id:** ID de la llamada en curso, si la hay
- **call_results:** Resultados de llamadas anteriores en esta conversación

## Intenciones que Reconoce el NLU

- **call_number:** El usuario pasó un número de teléfono específico y quiere que llamemos
- **search_and_call:** El usuario quiere que busquemos un tipo de negocio y llamemos
- **search_only:** El usuario quiere ver opciones antes de decidir
- **confirm:** El usuario está confirmando algo (eligiendo una opción, aceptando un turno)
- **cancel:** El usuario quiere cancelar la acción en curso
- **help:** El usuario necesita ayuda o no entendemos qué quiere

## Entidades que Extrae el NLU

- **phone_number:** Número de teléfono si lo proporcionó
- **service_type:** Tipo de servicio (dentista, peluquería, mecánico, restaurante, etc.)
- **location:** Ubicación o barrio
- **date_preference:** Cuándo quiere el turno (hoy, mañana, esta semana, lunes, etc.)
- **time_preference:** Horario preferido (mañana, tarde, noche, 15:00, etc.)
- **specific_request:** Cualquier pedido específico
- **selected_option:** Si está eligiendo una opción presentada previamente

---

# PARTE 6: CONFIGURACIÓN Y SETUP

## Cuentas y API Keys Necesarias

Antes del hackathon hay que crear todas estas cuentas y tener las keys listas:

**Twilio (twilio.com):** Crear cuenta, obtener Account SID y Auth Token. Activar el WhatsApp Sandbox desde la consola (Messaging → Try it out → WhatsApp). Comprar un número de teléfono para llamadas de voz (cuesta aproximadamente 1 dólar por mes). El sandbox de WhatsApp asigna un número de Twilio al que los usuarios mandan un código de unión para participar.

**ElevenLabs (elevenlabs.io):** Crear cuenta, obtener API Key. Explorar el dashboard de Conversational AI y familiarizarse con la documentación de Agentic Functions. El hackathon probablemente da créditos de ElevenLabs.

**OpenAI (platform.openai.com):** Crear cuenta, obtener API Key. Verificar créditos disponibles. El hackathon probablemente da créditos de OpenAI.

**Google Cloud (console.cloud.google.com):** Crear proyecto, habilitar la Places API y la Places Details API. Crear una API Key y configurar restricciones. Google da 200 dólares de crédito gratis mensual que más que alcanza.

**ngrok (ngrok.com):** Crear cuenta gratuita, instalar ngrok, obtener auth token. ngrok expone el servidor local a internet para que Twilio pueda enviar webhooks.

## Variables de Entorno

El proyecto necesita las siguientes variables de entorno:

- TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_NUMBER, TWILIO_PHONE_NUMBER
- ELEVENLABS_API_KEY, ELEVENLABS_AGENT_ID, ELEVENLABS_VOICE_ID
- OPENAI_API_KEY
- GOOGLE_PLACES_API_KEY
- BASE_URL (la URL pública de ngrok), PORT, DEBUG

## Dependencias Python

El proyecto usa: FastAPI y Uvicorn para el servidor, la librería de Twilio para WhatsApp y llamadas, httpx para llamadas HTTP async, la librería de OpenAI, websockets para la conexión con ElevenLabs, python-dotenv para variables de entorno, python-multipart para parsear los form data de Twilio, y pydantic para modelos de datos.

## Costos Estimados para las 24 Horas

El costo total estimado es de 5 a 10 dólares. El sandbox de WhatsApp de Twilio es gratis. El número de teléfono de Twilio cuesta 1 dólar. Las llamadas de prueba cuestan entre 2 y 5 dólares. ElevenLabs y OpenAI deberían estar cubiertos por los créditos del hackathon. Google Places tiene 200 dólares de crédito gratis. ngrok es gratuito.

---

# PARTE 7: PLAN DE EJECUCIÓN EN 24 HORAS

## Timeline Hora por Hora

### Hora 0-1: Setup (1 hora)
- Crear todas las cuentas si no están creadas
- Obtener todas las API keys
- Crear la estructura del proyecto
- Instalar dependencias
- Configurar ngrok
- Verificar que el sandbox de WhatsApp de Twilio funciona mandando un mensaje de prueba

### Hora 1-4: WhatsApp + NLU (3 horas)
- Implementar el webhook que recibe mensajes de WhatsApp
- Implementar la función que envía mensajes por WhatsApp
- Implementar el NLU con OpenAI (el system prompt y la función de parsing)
- Implementar el mensaje de bienvenida y ayuda
- Testear: mandar mensajes por WhatsApp y verificar que el bot responde y parsea correctamente las intenciones

### Hora 4-7: Google Places (3 horas)
- Implementar la búsqueda de negocios por tipo y ubicación
- Implementar la obtención de detalles (especialmente teléfono)
- Integrar con el flujo de WhatsApp para que cuando el usuario pida un servicio, le lleguen opciones
- Testear: pedir "dentista en Palermo" por WhatsApp y recibir opciones reales con teléfonos

### Hora 7-12: Agente de Voz — LA PARTE MÁS CRÍTICA (5 horas)
- Configurar el agente en ElevenLabs (via API o dashboard)
- Implementar la integración Twilio Voice con ElevenLabs Conversational AI via WebSocket (Media Streams)
- Implementar las Agentic Functions (validate_slot, report_result, ask_user)
- Hacer la primera llamada de prueba
- Testear: hacer una llamada real donde el agente habla
- Si la integración Twilio+ElevenLabs no funciona, activar el Plan B (ver sección de riesgos)

### Hora 12-16: Integración Completa (4 horas)
- Conectar todo el flujo de punta a punta: WhatsApp → NLU → Places → Agente de Voz → Reporte por WhatsApp
- Implementar el manejo de estados de conversación completo
- Implementar el reporte de resultados de llamada por WhatsApp (formateo bonito con emojis y datos claros)
- Manejar edge cases: negocio sin teléfono, llamada sin respuesta, error de conexión, usuario cancela
- Testear: flujo completo end-to-end al menos 3 veces

### Hora 16-20: Pulido y Stretch Goals (4 horas)
- Transcripción de audios de WhatsApp con Whisper
- Modo enjambre si da el tiempo (llamar a varios en paralelo)
- Mejorar la presentación de los mensajes de WhatsApp (formato, emojis, claridad)
- Manejo robusto de errores con mensajes amigables al usuario
- Logging completo para debug

### Hora 20-24: Demo y Presentación (4 horas)
- Preparar una secuencia de demo en vivo con mensajes de WhatsApp pre-pensados
- Grabar un video de backup por si la demo en vivo falla
- Armar 3-5 slides: el problema (30 seg), la solución Vocero (30 seg), demo en vivo (2-3 min), arquitectura técnica (30 seg), impacto y futuro (30 seg)
- Ensayar la presentación 2-3 veces

## División de Trabajo

### Persona 1: Backend + Integraciones
Se encarga del setup inicial, el webhook de WhatsApp, el NLU con OpenAI, la integración con Google Places, y el orquestador principal que conecta todo.

### Persona 2: Voz + ElevenLabs
Se encarga de configurar el agente de ElevenLabs, implementar la integración de Twilio Voice con ElevenLabs via WebSocket, definir las Agentic Functions, y testear las llamadas.

### Persona 3 (si hay): Demo + UX + Stretch
Se encarga de preparar la demo y presentación, implementar la transcripción de audios con Whisper, mejorar la UX de los mensajes de WhatsApp, testear el flujo end-to-end, y tener listo el Plan B.

---

# PARTE 8: PLAN B Y MANEJO DE RIESGOS

## Riesgo 1: La integración ElevenLabs + Twilio Voice no funciona

Este es el riesgo más grande. La conexión via WebSocket entre Twilio Media Streams y ElevenLabs Conversational AI puede tener problemas de formato de audio, latencia o compatibilidad.

**Plan B:** Simular la llamada completa. En vez de hacer una llamada real, usar dos instancias de ElevenLabs Conversational AI: una que actúa como el agente Vocero y otra que simula una recepcionista. El audio se genera y se puede reproducir o transcribir para mostrar en el demo. Para el jurado, esto demuestra igualmente la calidad conversacional y el uso de Agentic Functions. Se explica que en producción se conectaría a Twilio Voice.

## Riesgo 2: Google Places no devuelve teléfonos

No todos los negocios en Google Places tienen teléfono listado, especialmente en Buenos Aires.

**Plan B:** Crear un JSON con negocios de ejemplo con datos completos (nombre, dirección, teléfono real o de prueba) para usar durante el demo. Mostrar que la integración con Places funciona pero tener datos de respaldo que garanticen una demo fluida.

## Riesgo 3: Limitaciones del sandbox de WhatsApp

El sandbox de Twilio permite hasta 3 usuarios registrados por defecto. Los mensajes tienen que ir y venir desde números registrados.

**Mitigación:** Registrar los teléfonos de todos los integrantes del equipo antes del hackathon. Para el demo, usar un solo teléfono previamente verificado.

## Riesgo 4: Latencia alta en las respuestas

La cadena completa (Twilio → backend → OpenAI → Google Places → Twilio) puede tardar varios segundos.

**Mitigación:** Enviar mensajes intermedios de "procesando..." inmediatamente al usuario para que sepa que el bot está trabajando. Usar GPT-4o-mini que es mucho más rápido que GPT-4o para el NLU.

---

# PARTE 9: QUÉ EVALÚA EL JURADO Y CÓMO GANAMOS

## Calidad Conversacional

El agente de voz tiene que sonar natural, manejar interrupciones, y tener latencia baja. Esto se logra con una buena selección de voz en ElevenLabs (elegir una voz en español que suene profesional pero cálida) y un system prompt bien diseñado que le diga exactamente cómo comportarse.

## Uso de Agentic Functions

El jurado de ElevenLabs va a mirar específicamente cómo usamos su tecnología de tool calling. Por eso definimos tres herramientas claras (validate_slot, report_result, ask_user) que demuestran que el agente toma decisiones informadas durante la llamada y no solo sigue un script.

## Calidad del Match

Cuando presentamos opciones al usuario, las rankeamos por rating de Google y las mostramos con toda la información relevante. Si implementamos el modo enjambre, el ranking combina disponibilidad más temprana, rating y distancia.

## Experiencia de Usuario

WhatsApp como interfaz es nuestro diferenciador más fuerte. Cero fricción, cero curva de aprendizaje. El jurado va a poder probarlo desde su propio teléfono en 10 segundos.

---

# PARTE 10: NOTAS PARA EL DESARROLLO

## Prioridades de Implementación (en orden)

1. Hacer que WhatsApp funcione (recibir y enviar mensajes). Sin esto no hay demo.
2. Hacer que el NLU funcione (parsear mensajes y entender intenciones). Sin esto el bot es tonto.
3. Hacer que Google Places funcione (buscar negocios y obtener teléfonos). Esto da el wow factor de búsqueda.
4. Hacer que la llamada funcione (ElevenLabs + Twilio Voice). Esto es el core del challenge.
5. Conectar todo el flujo de punta a punta.
6. Pulir, stretch goals y preparar demo.

## Principios de Desarrollo

- **Simplicidad sobre elegancia.** Es un hackathon de 24 horas. El código tiene que funcionar, no ser bonito.
- **Logging agresivo.** Loggear absolutamente todo para debug rápido.
- **Fallar con gracia.** Si algo falla, mandar un mensaje amigable al usuario por WhatsApp, nunca crashear silenciosamente.
- **Estado en memoria.** No perder tiempo con bases de datos. Un diccionario en memoria alcanza para el demo con 3 usuarios.
- **Hardcodear lo que haga falta para el demo.** Si Google Places no devuelve teléfono, tener un fallback hardcodeado. La demo tiene que funcionar sí o sí.

## Qué NO Hacer

- No hacer frontend web. WhatsApp es la interfaz.
- No hacer autenticación ni login. Es un prototipo.
- No escribir tests unitarios extensivos. Testear manualmente por WhatsApp.
- No optimizar performance. No vas a tener más de 3 usuarios simultáneos.
- No hacer deploy en la nube. ngrok con localhost alcanza para la demo.
- No perder tiempo en README bonito hasta las últimas horas.
- No intentar resolver todos los edge cases. Cubrir el flujo feliz primero, después los bordes.
