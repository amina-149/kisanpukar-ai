from openai import OpenAI
import os, httpx, base64, tempfile
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """آپ کسان پکار AI ہیں — پاکستانی کسانوں کا ڈیجیٹل زرعی ماہر۔
آپ کو پاکستان کی زراعت کا مکمل علم ہے۔
ہمیشہ اردو میں جواب دیں۔ سادہ اور آسان زبان استعمال کریں۔
آپ ان موضوعات میں مدد کرتے ہیں:
- فصلوں کی بیماریاں اور علاج
- کھاد اور کیڑے مار دوائیں
- موسم اور آبپاشی
- منڈی کے بھاؤ
- حکومتی اسکیمیں
ہر جواب کے شروع میں 🌾 *کسان پکار AI* لکھیں۔
جواب مختصر، واضح اور عملی ہو۔"""


async def chat_urdu(message: str, phone: str, name: str = "") -> str:
    """Text message ka Urdu jawab"""

    # START command — welcome message
    if message.strip().upper() in ["START", "ہیلو", "HELLO", "HI", "السلام"] or "join list-stream" in message.lower():
        return """🌾 *کسان پکار AI میں خوش آمدید!*

السلام علیکم! میں آپ کا زرعی ڈیجیٹل ساتھی ہوں۔

آپ مجھ سے یہ کر سکتے ہیں:
📸 فصل کی *تصویر بھیجیں* ← بیماری کی تشخیص
🎤 *آواز میں سوال* پوچھیں ← فوری جواب
💬 کچھ بھی *لکھ کر* پوچھیں ← زرعی مشورہ
📊 *ریٹ* لکھیں ← آج کے منڈی بھاؤ

*کسان پکار — ہر قدم پر آپ کے ساتھ* 🇵🇒"""

    # Market rates check
    rate_keywords = ["ریٹ", "بھاؤ", "قیمت", "rate", "price", "مارکیٹ", "منڈی"]
    if any(word in message.lower() for word in rate_keywords):
        return get_market_rates()

    # General agricultural chat
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": message}
            ],
            max_tokens=400
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Chat error: {e}")
        return "🌾 *کسان پکار AI*\n\nمعذرت، دوبارہ کوشش کریں۔"


async def analyze_image(image_url: str) -> str:
    """Crop disease detection from image using GPT-4o Vision"""

    try:
        # Image download with Twilio auth
        async with httpx.AsyncClient(
            timeout=60,
            follow_redirects=True
        ) as http:
            img = await http.get(
                image_url,
                auth=(
                    os.getenv("TWILIO_ACCOUNT_SID"),
                    os.getenv("TWILIO_AUTH_TOKEN")
                ),
                headers={"User-Agent": "KisanPukarAI/1.0"}
            )
        
        if img.status_code != 200:
            return "🌾 *کسان پکار AI*\n\nتصویر نہیں مل سکی۔ دوبارہ بھیجیں۔"

        img_b64 = base64.b64encode(img.content).decode()

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{img_b64}"
                        }
                    },
                    {
                        "type": "text",
                        "text": """🌾 کسان پکار AI کی طرف سے اس فصل کی تصویر دیکھ کر اردو میں بتائیں:

1. 🌱 فصل کا نام کیا ہے؟
2. 🦠 کوئی بیماری یا کیڑا ہے؟ (نام بتائیں)
3. 💊 علاج کیا ہے؟ (دوائی کا نام)
4. ⚠️ آئندہ کیا احتیاط کریں؟
5. 📞 اگر سنگین ہو تو زرعی ماہر سے ملیں

سادہ اردو میں مختصر جواب دیں۔"""
                    }
                ]
            }],
            max_tokens=500
        )
        return response.choices[0].message.content

    except Exception as e:
        print(f"Image analysis error: {e}")
        return """🌾 *کسان پکار AI*

تصویر کا تجزیہ نہیں ہو سکا۔
براہ کرم:
• واضح روشنی میں تصویر لیں
• فصل قریب سے دکھائیں
• دوبارہ بھیجیں"""


async def handle_voice(audio_url: str) -> str:
    """Voice message: Download → Whisper STT → GPT-4o → Urdu reply"""

    try:
        # Audio download with Twilio auth
        async with httpx.AsyncClient(
            timeout=60,
            follow_redirects=True
        ) as http:
            audio = await http.get(
                audio_url,
                auth=(
                    os.getenv("TWILIO_ACCOUNT_SID"),
                    os.getenv("TWILIO_AUTH_TOKEN")
                ),
                headers={"User-Agent": "KisanPukarAI/1.0"}
            )
        
        if audio.status_code != 200:
            return "🌾 *کسان پکار AI*\n\nآواز نہیں مل سکی۔ دوبارہ بھیجیں۔"

        # Temp file mein save karo
        with tempfile.NamedTemporaryFile(
            suffix=".ogg", delete=False
        ) as f:
            f.write(audio.content)
            temp_path = f.name

        # Whisper se Urdu transcription
        with open(temp_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="ur"
            )

        os.unlink(temp_path)

        transcribed_text = transcript.text
        print(f"Voice transcribed: {transcribed_text}")

        # Transcribed text ka jawab lo
        reply = await chat_urdu(transcribed_text, "voice_user")
        return f"🎤 *آپ نے کہا:* {transcribed_text}\n\n{reply}"

    except Exception as e:
        print(f"Voice error: {e}")
        return """🌾 *کسان پکار AI*

آواز سمجھ نہیں آئی۔
براہ کرم:
• واضح آواز میں بولیں
• شور والی جگہ سے دور جائیں
• دوبارہ کوشش کریں"""


def get_market_rates() -> str:
    """Today's mandi rates in Urdu"""
    from datetime import datetime
    today = datetime.now().strftime("%d/%m/%Y")

    return f"""📊 *کسان پکار AI — آج کے منڈی ریٹ*
🗓️ تاریخ: {today}

*اناج:*
🌾 گندم: 3800-4200 روپے/من
🌽 مکئی: 2800-3100 روپے/من
🌾 چاول: 5500-6200 روپے/من

*نقد آور فصلیں:*
🌿 کپاس: 8500-9200 روپے/من
🎋 گنا: 350-380 روپے/من

*سبزیاں:*
🥔 آلو: 1200-1800 روپے/من
🧅 پیاز: 2200-2800 روپے/من
🍅 ٹماٹر: 1500-3000 روپے/من
🌶️ مرچ: 4000-6000 روپے/من

⚠️ _یہ تخمینی قیمتیں ہیں_
📍 _تازہ ریٹ کے لیے مقامی منڈی سے رابطہ کریں_

*کسان پکار — پاکستانی کسان کا ڈیجیٹل ساتھی* 🇵🇰"""