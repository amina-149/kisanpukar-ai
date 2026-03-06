from fastapi import FastAPI, Form
from fastapi.responses import JSONResponse, HTMLResponse
from twilio.rest import Client
import os
from dotenv import load_dotenv
import ai_engine, database, registration

load_dotenv()

app = FastAPI()

TWILIO_SID    = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN  = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_NUMBER = os.getenv("TWILIO_NUMBER")


def send_whatsapp(to: str, message: str):
    client = Client(TWILIO_SID, TWILIO_TOKEN)
    client.messages.create(
        from_=TWILIO_NUMBER,
        to=f"whatsapp:{to}",
        body=message
    )


# ── Webhook ───────────────────────────────────────────────

@app.post("/webhook")
async def webhook(
    From: str = Form(...),
    Body: str = Form(default=""),
    MediaUrl0: str = Form(default=None),
    MediaContentType0: str = Form(default=None)
):
    phone = From.replace("whatsapp:", "")
    reply = ""
    msg_type = "text"

    try:
        # ── Registration check ──
        if not database.is_registered(phone):
            reg_reply = await registration.handle_registration(Body, phone)
            if reg_reply:
                database.save_message(phone, "text", Body, reg_reply)
                send_whatsapp(phone, reg_reply)
                return JSONResponse(content={"status": "ok"})

        # ── Image — disease detection ──
        if MediaUrl0 and MediaContentType0 and "image" in MediaContentType0:
            msg_type = "image"
            reply = await ai_engine.analyze_image(MediaUrl0)

        # ── Voice message ──
        elif MediaUrl0 and MediaContentType0 and "audio" in MediaContentType0:
            msg_type = "voice"
            reply = await ai_engine.handle_voice(MediaUrl0)

        # ── Text ──
        else:
            msg_type = "text"
            user = database.get_user(phone)
            name = user.get("fields", {}).get("name", "") if user else ""
            reply = await ai_engine.chat_urdu(Body, phone, name)

    except Exception as e:
        reply = "🌾 *کسان پکار AI*\n\nمعذرت، کوئی مسئلہ آ گیا۔ دوبارہ کوشش کریں۔"
        print(f"Error: {e}")

    database.save_message(phone, msg_type, Body or "media", reply)
    send_whatsapp(phone, reply)
    return JSONResponse(content={"status": "ok"})


# ── Admin Dashboard ───────────────────────────────────────

@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard():
    try:
        s = database.get_dashboard_stats()
    except Exception as e:
        print(f"Dashboard error: {e}")
        s = {
            "total_users": 0, "registered_users": 0,
            "total_messages": 0, "top_city": "N/A", "top_crop": "N/A",
            "city_breakdown": {}, "crop_breakdown": {},
            "message_types": {"text": 0, "image": 0, "voice": 0}
        }

    city_rows = "".join(
        f"<tr><td>{city}</td><td><b>{count}</b></td></tr>"
        for city, count in s["city_breakdown"].items()
    ) or "<tr><td colspan='2' style='color:#999'>ابھی ڈیٹا نہیں</td></tr>"

    crop_rows = "".join(
        f"<tr><td>{crop}</td><td><b>{count}</b></td></tr>"
        for crop, count in s["crop_breakdown"].items()
    ) or "<tr><td colspan='2' style='color:#999'>ابھی ڈیٹا نہیں</td></tr>"

    return f"""<!DOCTYPE html>
<html dir="rtl" lang="ur">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>کسان پکار AI — ایڈمن</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Segoe UI',Arial,sans-serif;background:#f1f8f1;color:#1a1a1a}}
.header{{background:linear-gradient(135deg,#1B5E20,#388E3C);color:white;padding:22px 32px;
         display:flex;align-items:center;justify-content:space-between;
         box-shadow:0 3px 12px rgba(0,0,0,.2)}}
.header h1{{font-size:1.7em;margin-bottom:4px}}
.header p{{font-size:.85em;opacity:.85}}
.live{{display:inline-block;width:9px;height:9px;background:#69f0ae;
       border-radius:50%;animation:pulse 1.5s infinite;margin-right:6px}}
@keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:.3}}}}
.wrap{{max-width:1100px;margin:28px auto;padding:0 18px}}
.kpi{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:18px;margin-bottom:24px}}
.kpi-card{{background:white;border-radius:14px;padding:22px;text-align:center;
           box-shadow:0 2px 8px rgba(0,0,0,.07);border-top:4px solid #2E7D32}}
.kpi-icon{{font-size:2em;margin-bottom:8px}}
.kpi-num{{font-size:2.4em;font-weight:700;color:#1B5E20}}
.kpi-lbl{{color:#777;font-size:.9em;margin-top:6px}}
.row2{{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-bottom:24px}}
@media(max-width:640px){{.row2{{grid-template-columns:1fr}}}}
.card{{background:white;border-radius:14px;padding:22px;box-shadow:0 2px 8px rgba(0,0,0,.07)}}
.card h3{{color:#1B5E20;font-size:1em;margin-bottom:14px;padding-bottom:10px;
          border-bottom:2px solid #e8f5e9}}
table{{width:100%;border-collapse:collapse}}
td,th{{padding:9px 12px;text-align:right;border-bottom:1px solid #f5f5f5}}
th{{background:#e8f5e9;color:#2E7D32;font-size:.9em}}
.msg-row{{display:flex;gap:14px;flex-wrap:wrap}}
.msg-box{{flex:1;min-width:90px;border-radius:10px;padding:16px;text-align:center}}
.msg-n{{font-size:1.9em;font-weight:700}}
.footer{{text-align:center;padding:20px;color:#aaa;font-size:.8em}}
</style>
</head>
<body>

<div class="header">
  <div>
    <h1>🌾 کسان پکار AI</h1>
    <p><span class="live"></span>ایڈمن ڈیش بورڈ — پاکستانی کسانوں کا ڈیجیٹل ساتھی</p>
  </div>
  <span style="font-size:2.2em">🇵🇰</span>
</div>

<div class="wrap">

  <div class="kpi">
    <div class="kpi-card">
      <div class="kpi-icon">👨‍🌾</div>
      <div class="kpi-num">{s['total_users']}</div>
      <div class="kpi-lbl">کل صارفین</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-icon">✅</div>
      <div class="kpi-num">{s['registered_users']}</div>
      <div class="kpi-lbl">رجسٹرڈ کسان</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-icon">💬</div>
      <div class="kpi-num">{s['total_messages']}</div>
      <div class="kpi-lbl">کل پیغامات</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-icon">📍</div>
      <div class="kpi-num" style="font-size:1.4em">{s['top_city']}</div>
      <div class="kpi-lbl">سرفہرست شہر</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-icon">🌾</div>
      <div class="kpi-num" style="font-size:1.4em">{s['top_crop']}</div>
      <div class="kpi-lbl">مقبول ترین فصل</div>
    </div>
  </div>

  <!-- Message Types -->
  <div class="card" style="margin-bottom:20px">
    <h3>📊 پیغامات کی اقسام</h3>
    <div class="msg-row">
      <div class="msg-box" style="background:#e3f2fd">
        <div class="msg-n" style="color:#1565c0">{s['message_types'].get('text',0)}</div>
        <div>💬 متن</div>
      </div>
      <div class="msg-box" style="background:#f3e5f5">
        <div class="msg-n" style="color:#6a1b9a">{s['message_types'].get('image',0)}</div>
        <div>📸 تصویر</div>
      </div>
      <div class="msg-box" style="background:#fff3e0">
        <div class="msg-n" style="color:#e65100">{s['message_types'].get('voice',0)}</div>
        <div>🎤 آواز</div>
      </div>
    </div>
  </div>

  <div class="row2">
    <div class="card">
      <h3>📍 شہر کے مطابق کسان</h3>
      <table>
        <tr><th>شہر</th><th>تعداد</th></tr>
        {city_rows}
      </table>
    </div>
    <div class="card">
      <h3>🌾 فصل کے مطابق کسان</h3>
      <table>
        <tr><th>فصل</th><th>تعداد</th></tr>
        {crop_rows}
      </table>
    </div>
  </div>

</div>

<div class="footer">کسان پکار AI — پاکستانی کسان کا ڈیجیٹل ساتھی 🇵🇰 | © 2026</div>
<script>setTimeout(()=>location.reload(),30000)</script>
</body>
</html>"""


@app.get("/")
def root():
    return {
        "status": "KisanPukar AI چل رہا ہے! 🌾",
        "version": "2.0.0",
        "dashboard": "/admin"
    }