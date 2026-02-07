# Google Places API — Guía Completa

## 1. Overview

Usamos la **Places API (New)** — la versión nueva que usa POST requests y field masks.

**Endpoint principal**: `POST https://places.googleapis.com/v1/places:searchText`

---

## 2. Setup

### Crear API Key

1. Ir a https://console.cloud.google.com
2. Crear un proyecto nuevo (o usar uno existente)
3. Habilitar la API: APIs & Services → Library → buscar "Places API (New)" → Enable
4. Crear credenciales: APIs & Services → Credentials → Create Credentials → API Key
5. Restringir la API Key: solo permitir "Places API (New)"

### Pricing

- **$200 USD de crédito gratis** por mes (más que suficiente)
- Text Search Pro (con nombre, dirección, rating): ~$32 por 1000 requests
- Text Search Enterprise (con teléfono, horarios, website): ~$40 por 1000 requests
- Para el hackathon: ~50 búsquedas = menos de $2

---

## 3. Text Search — Buscar Negocios

### Request

```python
import httpx

async def search_businesses(
    http_client: httpx.AsyncClient,
    query: str,
    location: str | None = None,
    max_results: int = 5,
) -> list[dict]:
    """Buscar negocios con Google Places API (New).

    query: ej "dentista en Palermo, Buenos Aires"
    """
    # Construir el textQuery
    text_query = query
    if location:
        text_query = f"{query} en {location}"

    response = await http_client.post(
        "https://places.googleapis.com/v1/places:searchText",
        headers={
            "X-Goog-Api-Key": GOOGLE_PLACES_API_KEY,
            "X-Goog-FieldMask": ",".join([
                "places.id",
                "places.displayName",
                "places.formattedAddress",
                "places.nationalPhoneNumber",
                "places.internationalPhoneNumber",
                "places.rating",
                "places.userRatingCount",
                "places.currentOpeningHours",
                "places.websiteUri",
                "places.googleMapsUri",
                "places.location",
            ]),
            "Content-Type": "application/json",
        },
        json={
            "textQuery": text_query,
            "pageSize": max_results,
            "languageCode": "es",
        },
        timeout=15.0,
    )
    response.raise_for_status()
    data = response.json()
    return data.get("places", [])
```

### Response (ejemplo)

```json
{
  "places": [
    {
      "id": "ChIJxxxxxxxxxxxxxxxx",
      "displayName": {
        "text": "Consultorio Dr. García",
        "languageCode": "es"
      },
      "formattedAddress": "Av. Santa Fe 1234, C1059ABF Buenos Aires, Argentina",
      "nationalPhoneNumber": "011 4567-8900",
      "internationalPhoneNumber": "+54 11 4567-8900",
      "rating": 4.8,
      "userRatingCount": 156,
      "websiteUri": "https://drgarciadentista.com.ar",
      "googleMapsUri": "https://maps.google.com/?cid=...",
      "location": {
        "latitude": -34.5953,
        "longitude": -58.4006
      },
      "currentOpeningHours": {
        "openNow": true,
        "periods": [...]
      }
    }
  ]
}
```

---

## 4. Field Masks — Controlar qué datos pedir

El field mask es **obligatorio**. Controla qué campos recibís y cuánto te cobran.

### Campos disponibles (los que nos importan)

| Campo | Tier | Descripción |
|-------|------|-------------|
| `places.id` | ID Only (gratis) | ID único del lugar |
| `places.displayName` | Pro | Nombre del negocio |
| `places.formattedAddress` | Pro | Dirección completa |
| `places.location` | Pro | Lat/lng |
| `places.rating` | Enterprise | Rating promedio (0-5) |
| `places.userRatingCount` | Enterprise | Cantidad de reviews |
| `places.nationalPhoneNumber` | Enterprise | Teléfono local |
| `places.internationalPhoneNumber` | Enterprise | Teléfono internacional |
| `places.currentOpeningHours` | Enterprise | Horarios de apertura |
| `places.websiteUri` | Enterprise | Website |
| `places.googleMapsUri` | Pro | Link a Google Maps |

### Optimización de costos

Para la búsqueda inicial (mostrar opciones al usuario), pedir solo los campos que necesitamos:
```
X-Goog-FieldMask: places.id,places.displayName,places.formattedAddress,places.nationalPhoneNumber,places.rating,places.userRatingCount
```

---

## 5. Location Bias — Búsqueda por zona

Para buscar cerca de una ubicación específica:

```python
json={
    "textQuery": "dentista",
    "locationBias": {
        "circle": {
            "center": {
                "latitude": -34.5875,   # Palermo, Buenos Aires
                "longitude": -58.4106
            },
            "radius": 2000.0   # 2km de radio
        }
    },
    "pageSize": 5,
    "languageCode": "es",
}
```

### Coordenadas de barrios de Buenos Aires (para el demo)

| Barrio | Latitude | Longitude |
|--------|----------|-----------|
| Palermo | -34.5875 | -58.4106 |
| Recoleta | -34.5889 | -58.3939 |
| Belgrano | -34.5627 | -58.4563 |
| Caballito | -34.6186 | -58.4396 |
| San Telmo | -34.6216 | -58.3731 |
| Microcentro | -34.6037 | -58.3816 |
| Villa Crespo | -34.5991 | -58.4384 |

---

## 6. Formatear Resultados para WhatsApp

```python
def format_places_for_whatsapp(places: list[dict]) -> str:
    """Formatear resultados de Google Places para mensaje de WhatsApp."""
    if not places:
        return "No encontré resultados para esa búsqueda. Probá con otro barrio o tipo de servicio."

    lines = ["*Encontré estas opciones:*\n"]

    for i, place in enumerate(places, 1):
        name = place.get("displayName", {}).get("text", "Sin nombre")
        address = place.get("formattedAddress", "Sin dirección")
        phone = place.get("nationalPhoneNumber", "Sin teléfono")
        rating = place.get("rating")
        rating_count = place.get("userRatingCount", 0)

        rating_str = f"⭐ {rating} ({rating_count})" if rating else "Sin rating"

        lines.append(f"*{i}.* _{name}_ — {rating_str}")
        lines.append(f"   📍 {address}")

        if phone != "Sin teléfono":
            lines.append(f"   📞 {phone}")
        else:
            lines.append(f"   ⚠️ Sin teléfono disponible")

        lines.append("")  # línea vacía entre resultados

    lines.append("Respondé con el *número* de la opción para que llame.")

    return "\n".join(lines)
```

---

## 7. Manejar Negocios sin Teléfono

No todos los negocios tienen teléfono en Google Places. Estrategias:

1. **Filtrar**: Solo mostrar negocios que tengan teléfono
2. **Indicar**: Marcar los que no tienen con "Sin teléfono"
3. **Fallback**: Tener un JSON con datos de prueba para el demo

```python
def filter_places_with_phone(places: list[dict]) -> list[dict]:
    """Filtrar solo negocios que tienen teléfono."""
    return [
        p for p in places
        if p.get("nationalPhoneNumber") or p.get("internationalPhoneNumber")
    ]
```

---

## 8. Datos de Prueba para el Demo

Crear un archivo `demo_providers.json` con negocios de respaldo:

```json
[
    {
        "id": "demo_1",
        "displayName": {"text": "Consultorio Dental Dr. García"},
        "formattedAddress": "Av. Santa Fe 1234, Palermo, Buenos Aires",
        "nationalPhoneNumber": "011 4567-8900",
        "rating": 4.8,
        "userRatingCount": 156
    },
    {
        "id": "demo_2",
        "displayName": {"text": "Odontología Dra. López"},
        "formattedAddress": "Av. Córdoba 5678, Palermo, Buenos Aires",
        "nationalPhoneNumber": "011 9876-5432",
        "rating": 4.6,
        "userRatingCount": 89
    },
    {
        "id": "demo_3",
        "displayName": {"text": "Centro Dental Palermo"},
        "formattedAddress": "Honduras 4500, Palermo, Buenos Aires",
        "nationalPhoneNumber": "011 5555-1234",
        "rating": 4.5,
        "userRatingCount": 210
    }
]
```

---

## 9. Geocoding de nombres de barrios

Convertir "Palermo" a coordenadas. Dos opciones:

### Opción simple: Diccionario hardcodeado (recomendada para hackathon)

```python
BARRIOS_BA = {
    "palermo": (-34.5875, -58.4106),
    "recoleta": (-34.5889, -58.3939),
    "belgrano": (-34.5627, -58.4563),
    "caballito": (-34.6186, -58.4396),
    "san telmo": (-34.6216, -58.3731),
    "microcentro": (-34.6037, -58.3816),
    "villa crespo": (-34.5991, -58.4384),
    "almagro": (-34.6104, -58.4202),
    "nunez": (-34.5458, -58.4567),
    "colegiales": (-34.5745, -58.4495),
}

def get_location_coords(location: str) -> tuple[float, float] | None:
    """Obtener coordenadas de un barrio."""
    return BARRIOS_BA.get(location.lower().strip())
```

### Opción con API: Geocoding API de Google (si sobra tiempo)

```python
async def geocode(address: str, http_client: httpx.AsyncClient) -> tuple[float, float]:
    response = await http_client.get(
        "https://maps.googleapis.com/maps/api/geocode/json",
        params={
            "address": address,
            "key": GOOGLE_PLACES_API_KEY,
        }
    )
    data = response.json()
    location = data["results"][0]["geometry"]["location"]
    return location["lat"], location["lng"]
```

## 10. Links de referencia

- Text Search (New): https://developers.google.com/maps/documentation/places/web-service/text-search
- Place Details (New): https://developers.google.com/maps/documentation/places/web-service/place-details
- Data Fields: https://developers.google.com/maps/documentation/places/web-service/data-fields
- Choose Fields: https://developers.google.com/maps/documentation/places/web-service/choose-fields
- Pricing: https://developers.google.com/maps/billing-and-pricing/pricing
