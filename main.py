from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from openai import OpenAI
import os
import json
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """You are an AI assistant for John Rotors Insurance Agency, a commercial insurance brokerage specializing in business insurance.

## About John Insurance Agency
- Independent insurance broker with 25+ years experience
- Specializes in commercial insurance for small to mid-size businesses
- Coverage areas: General Liability, Professional Liability (E&O), Workers Compensation, Commercial Property, Cyber Liability, Business Auto
- Industries served: Technology companies, Professional services, Contractors, Restaurants, Retail, Healthcare
- Service area: Nationwide (licensed in all 50 states)
- Contact: (555) 123-4567 | info@johnrotorsinsurance.com

## Types of Insurance We Offer

### 1. General Liability Insurance
- Protects against: Bodily injury, property damage, advertising injury claims
- Who needs it: Nearly every business
- Typical cost: $500-$3,000/year depending on industry and size

### 2. Professional Liability (Errors & Omissions)
- Protects against: Professional mistakes, negligence, failure to deliver services
- Who needs it: Consultants, accountants, lawyers, IT professionals, architects
- Typical cost: $1,500-$4,000/year

### 3. Workers Compensation
- Protects: Employee injuries on the job
- Who needs it: Any business with employees (required by law in most states)

### 4. Commercial Property Insurance
- Protects: Building, equipment, inventory, furniture from fire, theft, vandalism

### 5. Cyber Liability Insurance
- Protects against: Data breaches, ransomware, cyber attacks
- Typical cost: $1,000-$3,000/year

### 6. Business Auto Insurance
- Protects: Vehicles used for business purposes

### 7. Business Owner's Policy (BOP)
- Bundles: General Liability + Commercial Property + Business Interruption

## Your Personality & Tone
- Professional but friendly and approachable
- Educational — insurance is confusing, help them understand
- Not pushy or sales-y
- Use real examples to make concepts clear
- Patient with questions

## Important Rules
1. Never quote exact prices — always say "typically ranges from X to Y"
2. Don't give legal advice
3. Always try to collect contact info if they want a quote
4. Lead qualification questions: Industry, # employees, revenue range, current coverage

## Lead Qualification Flow
When someone asks for a quote or shows interest, ask:
1. What industry/type of business?
2. How many employees?
3. Annual revenue (rough range is fine)?
4. Do you currently have any business insurance?
5. Best email and phone number to reach you?

Remember: Educate, qualify leads, and connect interested prospects with an agent. Be helpful, not pushy!"""


def log_lead(name, email, phone, business_type, num_employees, notes):
    try:
        creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
        if not creds_json:
            return False
        scopes = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = Credentials.from_service_account_info(json.loads(creds_json), scopes=scopes)
        gc = gspread.authorize(creds)
        sheet = gc.open("Insurance Leads").sheet1
        sheet.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            name or "", email or "", phone or "",
            business_type or "", num_employees or "", notes or "Chatbot lead"
        ])
        return True
    except Exception as e:
        print(f"Sheet log error: {e}")
        return False


def extract_lead(conversation_text):
    try:
        r = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": f"""
Extract contact info from this conversation. Return ONLY JSON, no markdown:
{{"name":null,"email":null,"phone":null,"business_type":null,"num_employees":null,"has_contact_info":false}}
Set has_contact_info true only if email OR phone is present.
Conversation:
{conversation_text}
"""}],
            max_tokens=150,
            temperature=0
        )
        raw = r.choices[0].message.content.strip().strip("```json").strip("```").strip()
        return json.loads(raw)
    except:
        return None


class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]


@app.get("/", response_class=HTMLResponse)
async def root():
    with open("static/index.html") as f:
        return f.read()


@app.post("/chat")
async def chat(req: ChatRequest):
    msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
    msgs += [{"role": m.role, "content": m.content} for m in req.messages]

    def stream():
        full_response = ""
        for chunk in client.chat.completions.create(
            model="gpt-4o-mini",
            messages=msgs,
            max_tokens=600,
            temperature=0.7,
            stream=True
        ):
            delta = chunk.choices[0].delta.content or ""
            if delta:
                full_response += delta
                yield f"data: {json.dumps({'content': delta})}\n\n"

        # Lead capture after response
        user_msgs = [m.content for m in req.messages if m.role == "user"]
        snippet = "\n".join(f"User: {m}" for m in user_msgs[-4:])
        lead = extract_lead(snippet)
        if lead and lead.get("has_contact_info"):
            log_lead(
                lead.get("name"), lead.get("email"), lead.get("phone"),
                lead.get("business_type"), lead.get("num_employees"), ""
            )

        yield "data: [DONE]\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")
