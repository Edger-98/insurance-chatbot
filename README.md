# Insurance AI Chatbot — Neme Co

Custom AI chatbot for insurance agencies. Built with FastAPI + OpenAI.

## Setup

1. Clone this repo
2. Copy `.env.example` to `.env` and fill in your keys
3. Run: `pip install -r requirements.txt`
4. Run: `uvicorn main:app --reload`
5. Open: http://localhost:8000

## Deploy to Render.com

1. Push to GitHub
2. Connect repo on render.com
3. Add environment variables (OPENAI_API_KEY, GOOGLE_CREDENTIALS_JSON)
4. Deploy

## Per-Client Customization

To customize for a new client:
1. Duplicate this repo
2. Update the SYSTEM_PROMPT in main.py with client's agency info
3. Update agent name in static/index.html
4. Deploy as new Render service
