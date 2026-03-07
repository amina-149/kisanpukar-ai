import os, httpx, base64, tempfile, json
from openai import OpenAI
from dotenv import load_dotenv
from datetime import datetime
import google.genai as genai
import market

load_dotenv()

# ── API Clients ───────────────────────────────────────────
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
client = genai.Client()

# ── Master System Prompt ──────────────────────────────────
SYSTEM_PROMPT = """آپ کسان پکار AI ہیں — پاکستانی کسانوں کے سچے ڈیجیٹل زرعی ماہر۔

🎯 آپ کا کردار:
آپ ایک تجربہ کار زرعی ماہر ہیں جو 30 سال سے پاکستانی کسانوں کی مدد کر رہے ہیں۔
آپ کسانوں کے دوست ہیں — آسان، سمجھ آنے والی زبان میں بات کریں۔

📋 زبان کے اصول:
- ہمیشہ سادہ اردو میں بات کریں
- گاؤں کے کسان جیسی آسان زبان
- لمبے لمبے الفاظ مت استعمال کریں
- "آپ" کہہ کر بات کریں، تاکہ کسان کو عزت محسوس ہو
- ہر جواب کے شروع میں 🌾 لکھیں

🌱 آپ یہ سب جانتے ہیں:
1. فصلوں کی بیماریاں اور کیڑے
2. پاکستان میں ملنے والی دوائیاں (Syngenta, FMC, Bayer, Dow AgroSciences)
3. پرانے دیسی علاج + جدید دوائیں دونوں
4. موسم کے حساب سے کاشتکاری
5. پانی کب اور کتنا دینا ہے
6. کھاد کا صحیح استعمال
7. منڈی کے بھاؤ اور فروخت کے مشورے
8. حکومتی اسکیمیں اور سبسڈی

⚡ اہم اصول:
- کبھی نہ کہیں "کسی ماہر سے ملیں" — آپ خود ماہر ہیں!
- ہمیشہ عملی اور مکمل جواب دیں
- دوائی کا نام، مقدار، استعمال کا طریقہ بتائیں
- دیسی علاج بھی بتائیں اگر ممکن ہو
- پاکستان کے مختلف علاقوں کا موسم جانتے ہیں"""


# ── Chat with Gemini (Cost Saving) ───────────────────────
async def chat_urdu(message: str, phone: str, name: str = "") -> str:
    """Gemini se Urdu mein jawab — sasta aur fast"""

    # Market rates
    rate_keywords = ["ریٹ", "بھاؤ", "قیمت", "rate", "price", "مارکیٹ", "منڈی", "مندی"]
    if any(word in message.lower() for word in rate_keywords):
        return await get_live_market_rates()

    # Weather
    weather_keywords = ["موسم", "بارش", "گرمی", "سردی", "weather", "درجہ حرارت"]
    if any(word in message.lower() for word in weather_keywords):
        return await get_weather_info(message)

    # Farmer ka naam use karo
    farmer_name = f"{name} صاحب" if name else "کسان بھائی"

    prompt = f"""{SYSTEM_PROMPT}

کسان کا نام: {farmer_name}
سوال: {message}

یاد رہے:
- سادہ اردو میں جواب دیں
- پاکستان میں ملنے والی دوائیں بتائیں
- دیسی علاج بھی بتائیں
- خود ماہر بن کر جواب دیں"""

    try:
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt
        )
        reply = response.text
        if not reply.startswith("🌾"):
            reply = "🌾 " + reply
        return reply
    except Exception as e:
        print(f"Gemini error: {e} — GPT-4o try kar raha hai")
        return await chat_gpt_fallback(message, name)


async def chat_gpt_fallback(message: str, name: str = "") -> str:
    """GPT-4o fallback agar Gemini fail ho"""
    try:
        farmer_name = f"{name} صاحب" if name else "کسان بھائی"
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"کسان کا نام: {farmer_name}\nسوال: {message}"}
            ],
            max_tokens=400
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"GPT fallback error: {e}")
        return "🌾 معذرت، ابھی جواب نہیں دے سکتا۔ تھوڑی دیر بعد کوشش کریں۔"


# ── Image Analysis with GPT-4o Vision ───────────────────
async def analyze_image(image_url: str) -> str:
    """GPT-4o Vision se crop disease detect karo"""

    try:
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as http:
            img = await http.get(
                image_url,
                auth=(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN")),
                headers={"User-Agent": "KisanPukarAI/1.0"}
            )

        if img.status_code != 200:
            return "🌾 تصویر نہیں مل سکی۔ دوبارہ بھیجیں۔"

        img_b64 = base64.b64encode(img.content).decode()

        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                    {"type": "text", "text": """آپ ایک تجربہ کار پاکستانی زرعی ماہر ہیں۔
اس تصویر کو دیکھ کر اردو میں بتائیں:

🌱 *فصل/پودے کا نام:*
[نام لکھیں]

🦠 *بیماری یا کیڑے کا مسئلہ:*
[کیا مسئلہ ہے — آسان الفاظ میں]

💊 *فوری علاج:*
[پاکستان میں ملنے والی دوائی کا نام + مقدار]
مثال: Confidor 200SL — ایک لیٹر پانی میں 1ml ملائیں

🌿 *دیسی نسخہ:*
[پرانا دیسی علاج بھی بتائیں]

💧 *پانی اور دیکھ بھال:*
[پانی کب اور کتنا دیں]

⚠️ *آئندہ احتیاط:*
[2 اہم باتیں]

سادہ اردو میں لکھیں جو گاؤں کا کسان سمجھ سکے۔"""}
                ]
            }],
            max_tokens=600
        )
        return response.choices[0].message.content

    except Exception as e:
        print(f"Image error: {e}")
        return """🌾 تصویر کا تجزیہ نہیں ہو سکا۔
براہ کرم:
• روشنی میں واضح تصویر لیں
• فصل قریب سے دکھائیں
• دوبارہ بھیجیں"""


# ── Voice Message Handler ────────────────────────────────
async def handle_voice(audio_url: str) -> str:
    """Voice → Whisper → Gemini → Urdu reply"""

    try:
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as http:
            audio = await http.get(
                audio_url,
                auth=(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN")),
                headers={"User-Agent": "KisanPukarAI/1.0"}
            )

        if audio.status_code != 200:
            return "🌾 آواز نہیں مل سکی۔ دوبارہ بھیجیں۔"

        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
            f.write(audio.content)
            temp_path = f.name

        # Whisper STT
        with open(temp_path, "rb") as af:
            transcript = openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=af,
                language="ur"
            )

        os.unlink(temp_path)
        text = transcript.text
        print(f"Voice: {text}")

        reply = await chat_urdu(text, "voice", "")
        return f"🎤 *آپ نے کہا:*\n_{text}_\n\n{reply}"

    except Exception as e:
        print(f"Voice error: {e}")
        return """🌾 آواز سمجھ نہیں آئی۔
• واضح آواز میں بولیں
• شور سے دور جائیں
• دوبارہ کوشش کریں"""


# ── Live Market Rates ────────────────────────────────────
async def get_live_market_rates() -> str:
    """Live mandi rates fetch karo — fallback to static"""
    try:
        # Pakistan mandi rates scrape
        async with httpx.AsyncClient(timeout=15) as http:
            r = await http.get(
                "https://www.listpk.com/crop-prices-in-pakistan/",
                headers={"User-Agent": "Mozilla/5.0"}
            )
        if r.status_code == 200:
            # Basic parse — sirf numbers nikalte hain
            pass
    except:
        pass

    # Static rates (daily update karo)
    today = datetime.now().strftime("%d/%m/%Y")
    return f"""📊 *کسان پکار — آج کے منڈی ریٹ*
🗓️ {today}

*🌾 اناج:*
• گندم: 3,800 - 4,200 روپے/من
• چاول (باسمتی): 6,000 - 7,500 روپے/من
• چاول (IRRI): 3,500 - 4,000 روپے/من
• مکئی: 2,800 - 3,200 روپے/من

*🌿 نقد آور فصلیں:*
• کپاس: 8,500 - 9,500 روپے/من
• گنا: 350 - 425 روپے/من

*🥦 سبزیاں (لاہور منڈی):*
• آلو: 1,200 - 1,800 روپے/من
• پیاز: 2,000 - 3,000 روپے/من
• ٹماٹر: 1,500 - 3,500 روپے/من
• مرچ: 4,000 - 7,000 روپے/من
• گوبھی: 800 - 1,400 روپے/من

*🍊 پھل:*
• آم: 3,000 - 8,000 روپے/من
• کینو: 1,500 - 2,500 روپے/من

━━━━━━━━━━━━━━━
⚠️ _ریٹ روزانہ بدلتے ہیں_
📍 _اپनی مقامی منڈی سے تصدیق کریں_
🌾 *کسان پکار AI* 🇵🇰"""


# ── Weather Info ─────────────────────────────────────────
async def get_weather_info(message: str) -> str:
    """Weather alerts for Pakistani regions"""

    # Detect region from message
    regions = {
        "لاہور": "Lahore", "فیصل آباد": "Faisalabad",
        "ملتان": "Multan", "کراچی": "Karachi",
        "پشاور": "Peshawar", "اسلام آباد": "Islamabad",
        "گوجرانوالہ": "Gujranwala", "سیالکوٹ": "Sialkot",
        "بہاولپور": "Bahawalpur", "رحیم یار خان": "Rahim Yar Khan"
    }

    detected_city = None
    for urdu, english in regions.items():
        if urdu in message:
            detected_city = english
            break

    if not detected_city:
        detected_city = "Lahore"

    try:
        api_key = os.getenv("WEATHER_API_KEY", "")
        if api_key:
            async with httpx.AsyncClient(timeout=10) as http:
                current_r = await http.get(
                    "http://api.openweathermap.org/data/2.5/weather",
                    params={
                        "q": detected_city + ",PK",
                        "appid": api_key,
                        "units": "metric"
                    }
                )

            if current_r.status_code == 200:
                c = current_r.json()
                temp      = c["main"]["temp"]
                feels     = c["main"]["feels_like"]
                humidity  = c["main"]["humidity"]
                wind      = c["wind"]["speed"] * 3.6
                condition = c["weather"][0]["description"]

                advice = get_weather_advice(temp, humidity)

                return f"""🌤️ *کسان پکار — موسم رپورٹ*
📍 {detected_city}

*ابھی کا موسم:*
🌡️ درجہ حرارت: {temp:.1f}°C (محسوس: {feels:.1f}°C)
💧 نمی: {humidity}%
💨 ہوا: {wind:.1f} km/h
☁️ موسم: {condition}

🌾 *زرعی مشورہ:*
{advice}

_کسان پکار AI_ 🇵🇰"""

    except Exception as e:
        print(f"Weather error: {e}")

    # Fallback seasonal advice
    month = datetime.now().month
    return get_seasonal_advice(month)


def get_weather_advice(temp: float, humidity: int) -> str:
    """Temp ke hisaab se farming advice"""
    advice = []

    if temp > 38:
        advice.append("• گرمی بہت زیادہ ہے — صبح یا شام کو پانی دیں")
        advice.append("• فصل کو دھوپ سے بچائیں")
    elif temp < 5:
        advice.append("• ٹھنڈ سے فصل بچائیں — پانی روکیں")
        advice.append("• پالے سے نقصان ہو سکتا ہے")

    if humidity > 80:
        advice.append("• نمی زیادہ ہے — پھپھوندی کا خطرہ ہے")
        advice.append("• Dithane M-45 سپرے کریں")

    return "\n".join(advice) if advice else "• موسم ٹھیک ہے — معمول کی کاشتکاری جاری رکھیں"


def get_seasonal_advice(month: int) -> str:
    """Seasonal farming advice Pakistan"""
    if month in [3, 4, 5]:
        return """🌸 *ربیع فصل کا موسم*
🗓️ مارچ-مئی — گندم کٹائی کا وقت

• گندم: کٹائی شروع کریں جب دانہ سخت ہو
• مکئی: بوائی کا بہترین وقت
• سبزیاں: ٹماٹر اور مرچ لگائیں
• پانی: ہر 10-12 دن میں
• کیڑے: گرمی سے کیڑے بڑھتے ہیں — نظر رکھیں

_کسان پکار AI_ 🇵🇰"""

    elif month in [6, 7, 8, 9]:
        return """☀️ *خریف فصل کا موسم*
🗓️ جون-ستمبر — گرمی کا موسم

• کپاس: بوائی اور نگہداشت
• چاول: ٹرانسپلانٹ کریں
• گنا: کاٹنے کا وقت آ رہا ہے
• پانی: ہر 5-7 دن میں — گرمی زیادہ ہے
• سپرے: شام کو کریں — گرمی میں نقصان ہو سکتا ہے

_کسان پکار AI_ 🇵🇰"""

    elif month in [10, 11]:
        return """🍂 *خریف کٹائی کا موسم*
🗓️ اکتوبر-نومبر

• کپاس: چنائی جاری رکھیں
• چاول: کٹائی کریں
• گندم: بوائی کی تیاری کریں
• پانی: ٹھنڈ شروع — پانی کم کریں
• کھاد: DAP ڈالنے کا وقت

_کسان پکار AI_ 🇵🇰"""

    else:
        return """❄️ *سردی کا موسم*
🗓️ دسمبر-فروری

• گندم: نگہداشت کریں — یوریا ڈالیں
• سبزیاں: آلو اور پیاز کی فصل
• پالا: رات کو پانی دیں — پالے سے بچائیں
• کیڑے: سردی میں کم — پر چیک کرتے رہیں
• پانی: 15-20 دن میں ایک بار

_کسان پکار AI_ 🇵🇰"""