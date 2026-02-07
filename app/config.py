from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://vocero:vocero@localhost:5432/vocero"

    # Twilio (for outbound phone calls via ElevenLabs)
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""

    # Meta WhatsApp Cloud API
    meta_phone_number_id: str = ""
    meta_waba_id: str = ""
    meta_access_token: str = ""
    meta_webhook_verify_token: str = "vocero_verify"

    # ElevenLabs
    elevenlabs_api_key: str = ""
    elevenlabs_agent_id: str = ""
    elevenlabs_phone_number_id: str = ""

    # OpenAI
    openai_api_key: str = ""

    # Resend
    resend_api_key: str = ""
    resend_from_email: str = "vocero@yourdomain.com"

    # App
    app_base_url: str = "http://localhost:8000"
    debug: bool = True

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
