from fastapi import FastAPI, Form
from fastapi.responses import JSONResponse
from twilio.rest import Client
import os
from dotenv import load_dotenv
import ai_engine

load_dotenv()

app = FastAPI()

TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_NUMBER = os.getenv("TWILIO_NUMBER")

def send_whatsapp(to: str, message: str):
    client = Client(TWILIO_SID, TWILIO_TOKEN)
    client.messages.create(
        from_=TWILIO_NUMBER,
        to=f"whatsapp:{to}",
        body=message
    )

@app.post("/webhook")
async def webhook(
    From: str = Form(...),
    Body: str = Form(default=""),
    MediaUrl0: str = Form(default=None),
    MediaContentType0: str = Form(default=None)
):
    user_phone = From.replace("whatsapp:", "")
    reply = ""

    try:
        # Image message — crop disease
        if MediaUrl0 and MediaContentType0 and "image" in MediaContentType0:
            reply = await ai_engine.analyze_image(MediaUrl0)

        # Audio message — voice
        elif MediaUrl0 and MediaContentType0 and "audio" in MediaContentType0:
            reply = await ai_engine.handle_voice(MediaUrl0)

        # Text message
        else:
            reply = await ai_engine.chat_urdu(Body, user_phone)

    except Exception as e:
        reply = "معذرت، کوئی مسئلہ آ گیا۔ دوبارہ کوشش کریں۔"
        print(f"Error: {e}")

    send_whatsapp(user_phone, reply)
    return JSONResponse(content={"status": "ok"})

@app.get("/")
def root():
    return {"status": "AgriBot Pakistan Running! 🌾"}