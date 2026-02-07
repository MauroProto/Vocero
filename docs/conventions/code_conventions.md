# Code Conventions

## Project Structure
- **Routes** in `app/api/` — thin handlers that validate input and delegate to services.
- **Services** in `app/services/` — all business logic lives here.
- **Models** in `app/models/` — SQLAlchemy ORM definitions.
- **Schemas** in `app/schemas/` — Pydantic models for request/response validation.

## Error Handling
- Let FastAPI's exception handlers deal with HTTP errors.
- Services raise domain-specific exceptions (e.g., `ProviderNotFoundError`, `CallFailedError`).
- Custom exception handlers in `app/main.py` map domain exceptions to HTTP responses.
- Don't wrap internal calls in try/catch unless there's a specific recovery action.

## Logging
- Use Python's `logging` module with structured context.
- Log at service boundaries: incoming requests, outbound API calls, call status changes.
- Never log sensitive data (API keys, user phone numbers in full).
- No `print()` statements — use `logger.debug()` / `logger.info()` instead.

## Async
- All route handlers and service methods are `async`.
- Use `httpx.AsyncClient` for outbound HTTP calls.
- Use SQLAlchemy async sessions for database operations.

## Configuration
- All config via environment variables, loaded through `app/config.py` (Pydantic `BaseSettings`).
- Never hardcode API keys, URLs, or secrets.

## Dependencies
- Use FastAPI's `Depends()` for dependency injection (db sessions, config, services).
- Keep the dependency chain shallow — max 2 levels deep.

## Naming
- Files: `snake_case.py`
- Classes: `PascalCase`
- Functions/variables: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- API routes: `/kebab-case` or `/snake_case` (match Twilio's conventions for webhooks)
