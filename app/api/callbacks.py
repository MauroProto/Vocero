from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["callbacks"])


@router.post("/call-status")
async def call_status_callback():
    """Twilio call status webhook — implemented in feature outbound_voice_call."""
    return {"status": "not_implemented"}
