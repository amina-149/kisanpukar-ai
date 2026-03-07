from fastapi import FastAPI, Form, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from twilio.rest import Client
import os, requests as req
from dotenv import load_dotenv
from datetime import datetime
import ai_engine, database, registration

load_dotenv()

app = FastAPI(title="KisanPukar AI", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

TWILIO_SID    = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN  = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_NUMBER = os.getenv("TWILIO_NUMBER")
AT_TOKEN      = os.getenv("AIRTABLE_TOKEN")
AT_BASE       = os.getenv("AIRTABLE_BASE_ID")
AT_HEADERS    = lambda: {"Authorization": f"Bearer {AT_TOKEN}", "Content-Type": "application/json"}


def send_whatsapp(to: str, message: str):
    client = Client(TWILIO_SID, TWILIO_TOKEN)
    client.messages.create(from_=TWILIO_NUMBER, to=f"whatsapp:{to}", body=message)


# ══════════════════════════════════════════════
# WEBHOOK
# ══════════════════════════════════════════════

@app.post("/webhook")
async def webhook(
    From: str = Form(...),
    Body: str = Form(default=""),
    MediaUrl0: str = Form(default=None),
    MediaContentType0: str = Form(default=None)
):
    phone    = From.replace("whatsapp:", "")
    reply    = ""
    msg_type = "text"
    
    print(f"[WEBHOOK] Received from {phone}: {Body}")
    
    try:
        if not database.is_registered(phone):
            print(f"[REG] User {phone} not registered, handling registration...")
            reg_reply = await registration.handle_registration(Body, phone)
            if reg_reply:
                print(f"[REG] Sending welcome message")
                database.save_message(phone, "text", Body, reg_reply)
                send_whatsapp(phone, reg_reply)
                print(f"[REG] Message sent successfully")
                return JSONResponse(content={"status": "ok"})
            else:
                print(f"[REG] reg_reply is None, continuing to chat...")

        if MediaUrl0 and MediaContentType0 and "image" in MediaContentType0:
            msg_type = "image"
            reply = await ai_engine.analyze_image(MediaUrl0)
        elif MediaUrl0 and MediaContentType0 and "audio" in MediaContentType0:
            msg_type = "voice"
            reply = await ai_engine.handle_voice(MediaUrl0)
        else:
            msg_type = "text"
            user   = database.get_user(phone)
            name   = user.get("fields", {}).get("Name", "") if user else ""
            reply  = await ai_engine.chat_urdu(Body, phone, name)
    except Exception as e:
        import traceback
        reply = "🌾 *کسان پکار AI*\n\nمعذرت، کوئی مسئلہ آ گیا۔ دوبارہ کوشش کریں۔"
        print(f"[ERROR] Webhook error: {e}")
        print(traceback.format_exc())

    if reply:
        print(f"[SEND] Sending to {phone}: {reply[:50]}...")
        database.save_message(phone, msg_type, Body or "media", reply)
        send_whatsapp(phone, reply)
    else:
        print(f"[WARN] No reply to send")
    
    return JSONResponse(content={"status": "ok"})


# ══════════════════════════════════════════════
# TEST WEBHOOK (for debugging)
# ══════════════════════════════════════════════

@app.get("/test-webhook/{phone}/{message}")
async def test_webhook(phone: str, message: str):
    """Test endpoint to bypass Twilio and test bot directly"""
    print(f"\n[TEST] Testing webhook with phone={phone}, message={message}")
    
    reply = ""
    try:
        if not database.is_registered(phone):
            print(f"[TEST-REG] User {phone} not registered")
            reg_reply = await registration.handle_registration(message, phone)
            if reg_reply:
                print(f"[TEST-REG] Got registration reply")
                database.save_message(phone, "text", message, reg_reply)
                return JSONResponse(content={"reply": reg_reply, "type": "registration"})
        
        user = database.get_user(phone)
        name = user.get("fields", {}).get("Name", "") if user else ""
        reply = await ai_engine.chat_urdu(message, phone, name)
        database.save_message(phone, "text", message, reply)
        return JSONResponse(content={"reply": reply, "type": "chat"})
    except Exception as e:
        import traceback
        print(f"[TEST-ERROR] {e}")
        print(traceback.format_exc())
        return JSONResponse(content={"error": str(e)}, status_code=500)


# ══════════════════════════════════════════════
# API — STATS
# ══════════════════════════════════════════════

@app.get("/api/stats")
async def api_stats():
    try:
        return JSONResponse(content=database.get_dashboard_stats())
    except Exception as e:
        return JSONResponse(content={"error": str(e), "total_users": 0,
            "registered_users": 0, "total_messages": 0,
            "region_breakdown": {}, "crop_breakdown": {},
            "message_types": {"text": 0, "image": 0, "voice": 0}})


# ══════════════════════════════════════════════
# API — FARMERS
# ══════════════════════════════════════════════

@app.get("/api/farmers")
async def api_farmers(limit: int = 100):
    try:
        r = req.get(
            f"https://api.airtable.com/v0/{AT_BASE}/users",
            headers=AT_HEADERS(),
            params={"maxRecords": limit,
                    "sort[0][field]": "Created At",
                    "sort[0][direction]": "desc"}
        )
        records = r.json().get("records", [])
        farmers = [{
            "id":         rec.get("id"),
            "name":       rec["fields"].get("Name", "نامعلوم"),
            "phone":      rec["fields"].get("Phone", ""),
            "region":     rec["fields"].get("Region", ""),
            "language":   rec["fields"].get("Language", "urdu"),
            "crop":       rec["fields"].get("crop_type", ""),
            "acres":      rec["fields"].get("land_acres", 0),
            "registered": rec["fields"].get("registered", False),
            "created_at": rec["fields"].get("Created At", "")
        } for rec in records]
        return JSONResponse(content={"farmers": farmers, "total": len(farmers)})
    except Exception as e:
        return JSONResponse(content={"farmers": [], "total": 0, "error": str(e)})


# ══════════════════════════════════════════════
# API — MESSAGES
# ══════════════════════════════════════════════

@app.get("/api/messages")
async def api_messages(limit: int = 50):
    try:
        r = req.get(
            f"https://api.airtable.com/v0/{AT_BASE}/Messages",
            headers=AT_HEADERS(),
            params={"maxRecords": limit,
                    "sort[0][field]": "created_at",
                    "sort[0][direction]": "desc"}
        )
        records = r.json().get("records", [])
        msgs = [{
            "phone":      f.get("fields", {}).get("phone_number", ""),
            "type":       f.get("fields", {}).get("message_type", "text"),
            "user_msg":   f.get("fields", {}).get("user_message", "")[:120],
            "bot_reply":  f.get("fields", {}).get("bot_reply", "")[:120],
            "created_at": f.get("fields", {}).get("created_at", "")
        } for f in records]
        return JSONResponse(content={"messages": msgs, "total": len(msgs)})
    except Exception as e:
        return JSONResponse(content={"messages": [], "total": 0, "error": str(e)})


# ══════════════════════════════════════════════
# API — BROADCAST
# ══════════════════════════════════════════════

@app.post("/api/broadcast")
async def api_broadcast(request: Request):
    try:
        body    = await request.json()
        message = body.get("message", "")
        region  = body.get("region", "all")
        crop    = body.get("crop", "all")
        if not message:
            return JSONResponse(content={"error": "Message required"}, status_code=400)

        formula = "{registered}=1"
        r = req.get(
            f"https://api.airtable.com/v0/{AT_BASE}/users",
            headers=AT_HEADERS(),
            params={"filterByFormula": formula, "fields[]": ["Phone", "Region", "crop_type"]}
        )
        records = r.json().get("records", [])
        sent = failed = 0
        for rec in records:
            f     = rec.get("fields", {})
            phone = f.get("Phone", "")
            if not phone: continue
            if region != "all" and f.get("Region", "") != region: continue
            if crop   != "all" and f.get("crop_type", "") != crop: continue
            try:
                send_whatsapp(phone, message)
                sent += 1
            except Exception as e:
                failed += 1
                print(f"Broadcast fail {phone}: {e}")

        return JSONResponse(content={
            "sent": sent, "failed": failed,
            "message": f"✅ {sent} کسانوں کو پیغام بھیجا گیا"
        })
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


# ══════════════════════════════════════════════
# API — COMPANIES
# ══════════════════════════════════════════════

@app.get("/api/companies")
async def api_companies():
    try:
        r = req.get(
            f"https://api.airtable.com/v0/{AT_BASE}/Companies",
            headers=AT_HEADERS()
        )
        records = r.json().get("records", [])
        companies = [{
            "id":       rec.get("id"),
            "name":     rec["fields"].get("company_name", ""),
            "type":     rec["fields"].get("company_type", ""),
            "contact":  rec["fields"].get("contact", ""),
            "region":   rec["fields"].get("region", ""),
            "products": rec["fields"].get("products", ""),
            "plan":     rec["fields"].get("plan", "free"),
            "active":   rec["fields"].get("active", False)
        } for rec in records]
        return JSONResponse(content={"companies": companies, "total": len(companies)})
    except Exception as e:
        return JSONResponse(content={"companies": [], "total": 0})


@app.post("/api/companies")
async def add_company(request: Request):
    try:
        body = await request.json()
        payload = {"records": [{"fields": {
            "company_name": body.get("name", ""),
            "company_type": body.get("type", ""),
            "contact":      body.get("contact", ""),
            "region":       body.get("region", ""),
            "products":     body.get("products", ""),
            "plan":         body.get("plan", "free"),
            "active":       True,
            "created_at":   datetime.now().isoformat()
        }}]}
        r = req.post(
            f"https://api.airtable.com/v0/{AT_BASE}/Companies",
            headers=AT_HEADERS(),
            json=payload
        )
        return JSONResponse(content={"success": True, "record": r.json()})
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


# ══════════════════════════════════════════════
# API — MARKET RATES
# ══════════════════════════════════════════════

@app.get("/api/market-rates")
async def api_market_rates():
    return JSONResponse(content={
        "updated_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "rates": {
            "اناج": [
                {"name": "گندم",  "min": 3800, "max": 4200, "unit": "من",  "trend": "up"},
                {"name": "مکئی", "min": 2800, "max": 3200, "unit": "من",  "trend": "stable"},
                {"name": "چاول", "min": 3500, "max": 4000, "unit": "من",  "trend": "up"},
            ],
            "سبزیاں": [
                {"name": "ٹماٹر", "min": 80,  "max": 120, "unit": "کلو", "trend": "up"},
                {"name": "آلو",   "min": 45,  "max": 65,  "unit": "کلو", "trend": "down"},
                {"name": "پیاز",  "min": 55,  "max": 80,  "unit": "کلو", "trend": "stable"},
                {"name": "مرچ",   "min": 100, "max": 200, "unit": "کلو", "trend": "up"},
            ],
            "پھل": [
                {"name": "سیب",  "min": 150, "max": 250, "unit": "کلو", "trend": "up"},
                {"name": "آم",   "min": 120, "max": 200, "unit": "کلو", "trend": "stable"},
                {"name": "آڑو",  "min": 100, "max": 180, "unit": "کلو", "trend": "up"},
            ]
        }
    })


# ══════════════════════════════════════════════
# API — HEALTH CHECK
# ══════════════════════════════════════════════

@app.get("/api/health")
async def health():
    return JSONResponse(content={
        "status": "online",
        "version": "3.0.0",
        "checks": {
            "api":      True,
            "airtable": bool(AT_TOKEN),
            "openai":   bool(os.getenv("OPENAI_API_KEY")),
            "gemini":   bool(os.getenv("GEMINI_API_KEY")),
            "twilio":   bool(TWILIO_SID),
            "weather":  bool(os.getenv("WEATHER_API_KEY")),
        },
        "timestamp": datetime.now().isoformat()
    })


# ══════════════════════════════════════════════
# ADMIN DASHBOARD
# ══════════════════════════════════════════════

@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard():
    try:
        with open("admin_dashboard.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>admin_dashboard.html not found — please upload it</h1>")


@app.get("/")
def root():
    return {
        "status": "🌾 KisanPukar AI چل رہا ہے!",
        "version": "3.0.0",
        "dashboard": "/admin",
        "api_docs": "/docs",
        "health": "/api/health"
    }
