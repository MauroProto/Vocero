from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["whatsapp"])


@router.post("/whatsapp")
async def whatsapp_webhook():
    """Twilio WhatsApp webhook — implemented in feature whatsapp_webhook."""
    return {"status": "not_implemented"}
