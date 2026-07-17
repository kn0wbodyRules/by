# BOQ Automation Tool — Backend

FastAPI backend for automated Bill of Quantities generation. Deterministic quantity engine +
pluggable rate table + ML correction-factor layer (fallback-only until real training data lands).

## Setup

1. **Install Docker Desktop** (enable WSL2 backend if prompted on Windows).
2. **Start Postgres:**
   ```
   docker compose up -d
   docker compose ps   # confirm "healthy"
   ```
3. **Create/activate the virtual environment and install dependencies:**
   ```
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```
4. **Copy `.env.example` to `.env`** and fill in real secrets (never commit `.env`):
   - `JWT_SECRET_KEY` — any random 64-char string
   - `SMTP_HOST`/`SMTP_USER`/`SMTP_PASSWORD` — real SMTP credentials for OTP email delivery.
     Leave blank in development — OTP codes are logged to the console instead.
   - `GEMINI_API_KEY` — for real floor-plan photo room detection. Leave `GEMINI_MOCK_MODE=true`
     to develop against a fixture response without a key.
5. **Run migrations:**
   ```
   alembic upgrade head
   ```
6. **Run the API:**
   ```
   uvicorn app.main:app --reload
   ```
7. Open **http://localhost:8000/docs** for the interactive Swagger UI — every endpoint can be
   tried directly from the browser without any frontend code.

## Known placeholders (replace before real use)

- `app/seed_data/rate_table_seed.json` — fabricated rates, NOT real Tamil Nadu PWD SOR figures.
- ML correction layer (`app/services/correction_service.py`) always returns
  `correction_factor=1.0`, `confidence="fallback"` until a real model is trained on real
  historical BOQ data and registered in `model_versions`.

## Running tests

```
pytest
```
