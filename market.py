import httpx
import json
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ── KPK Official Sources ──────────────────────────────────
KPK_SOURCES = [
    "http://fmis.kp.gov.pk",
    "https://zarat.kp.gov.pk",
    "https://narkh.pk"
]

# ── Static Rates (Daily Manual Update + Auto Fallback) ───
STATIC_RATES = {
    "peshawar": {
        "سبزیاں": {
            "ٹماٹر": {"min": 80, "max": 120, "unit": "کلو"},
            "آلو": {"min": 45, "max": 65, "unit": "کلو"},
            "پیاز": {"min": 55, "max": 80, "unit": "کلو"},
            "گوبھی": {"min": 40, "max": 60, "unit": "کلو"},
            "مٹر": {"min": 120, "max": 160, "unit": "کلو"},
            "بینگن": {"min": 50, "max": 70, "unit": "کلو"},
            "ٹینڈے": {"min": 60, "max": 90, "unit": "کلو"},
            "پالک": {"min": 30, "max": 50, "unit": "کلو"},
            "مرچ": {"min": 100, "max": 200, "unit": "کلو"},
        },
        "پھل": {
            "سیب": {"min": 150, "max": 250, "unit": "کلو"},
            "آم": {"min": 120, "max": 200, "unit": "کلو"},
            "کیلا": {"min": 80, "max": 120, "unit": "درجن"},
            "انگور": {"min": 200, "max": 350, "unit": "کلو"},
            "آڑو": {"min": 100, "max": 180, "unit": "کلو"},
            "ناشپاتی": {"min": 120, "max": 200, "unit": "کلو"},
        },
        "اناج": {
            "گندم": {"min": 3800, "max": 4200, "unit": "من"},
            "مکئی": {"min": 2800, "max": 3200, "unit": "من"},
            "چاول IRRI": {"min": 3500, "max": 4000, "unit": "من"},
        }
    },
    "lahore": {
        "سبزیاں": {
            "ٹماٹر": {"min": 70, "max": 110, "unit": "کلو"},
            "آلو": {"min": 40, "max": 60, "unit": "کلو"},
            "پیاز": {"min": 50, "max": 75, "unit": "کلو"},
            "گوبھی": {"min": 35, "max": 55, "unit": "کلو"},
            "مرچ": {"min": 90, "max": 180, "unit": "کلو"},
        },
        "اناج": {
            "گندم": {"min": 3900, "max": 4300, "unit": "من"},
            "کپاس": {"min": 8500, "max": 9500, "unit": "من"},
            "گنا": {"min": 350, "max": 425, "unit": "من"},
            "چاول باسمتی": {"min": 6000, "max": 7500, "unit": "من"},
        }
    },
    "multan": {
        "سبزیاں": {
            "ٹماٹر": {"min": 65, "max": 100, "unit": "کلو"},
            "آلو": {"min": 38, "max": 58, "unit": "کلو"},
            "پیاز": {"min": 48, "max": 70, "unit": "کلو"},
        },
        "اناج": {
            "گندم": {"min": 3800, "max": 4200, "unit": "من"},
            "کپاس": {"min": 8800, "max": 9800, "unit": "من"},
            "آم": {"min": 80, "max": 150, "unit": "کلو"},
        }
    }
}

# City name mapping (Urdu → key)
CITY_MAP = {
    "پشاور": "peshawar", "لاہور": "lahore", "ملتان": "multan",
    "فیصل آباد": "lahore", "کراچی": "lahore", "اسلام آباد": "peshawar",
    "نوشہرہ": "peshawar", "مردان": "peshawar", "ایبٹ آباد": "peshawar",
    "سوات": "peshawar", "دیر": "peshawar", "چارسدہ": "peshawar",
    "peshawar": "peshawar", "lahore": "lahore", "multan": "multan"
}


async def get_rates_for_city(city_urdu: str = "پشاور") -> str:
    """City ke rates Urdu mein do"""
    city_key = CITY_MAP.get(city_urdu, "peshawar")
    rates = STATIC_RATES.get(city_key, STATIC_RATES["peshawar"])
    today = datetime.now().strftime("%d/%m/%Y")

    msg = f"""📊 *کسان پکار — منڈی ریٹ*
📍 {city_urdu} | 🗓️ {today}

"""
    for category, items in rates.items():
        msg += f"*{category}:*\n"
        for item, price in items.items():
            msg += f"• {item}: {price['min']}-{price['max']} روپے/{price['unit']}\n"
        msg += "\n"

    msg += """━━━━━━━━━━━━━━━
💡 *کسان بھائی یاد رکھیں:*
منڈی ریٹ اور آپ کو ملنے والے ریٹ میں فرق ہوتا ہے۔
کسان پکار جلد آپ کو براہ راست خریدار سے ملائے گا!

⚠️ _تصدیق کے لیے مقامی منڈی سے پوچھیں_
🌾 *کسان پکار AI* 🇵🇰"""

    return msg


async def get_price_gap_analysis(crop: str, city: str = "پشاور") -> str:
    """Farmer price vs mandi price gap dikhao"""

    gaps = {
        "آلو": {"farmer": 25, "mandi": 50, "suggested": 42},
        "ٹماٹر": {"farmer": 40, "mandi": 90, "suggested": 70},
        "پیاز": {"farmer": 30, "mandi": 65, "suggested": 52},
        "گندم": {"farmer": 3600, "mandi": 4000, "suggested": 3850},
        "مکئی": {"farmer": 2400, "mandi": 3000, "suggested": 2750},
    }

    if crop in gaps:
        g = gaps[crop]
        saving = g["suggested"] - g["farmer"]
        return f"""💰 *{crop} — قیمت کا فرق*

👨‍🌾 آپ کو ملتا ہے: {g['farmer']} روپے/کلو
🏪 منڈی میں بکتا ہے: {g['mandi']} روپے/کلو
📉 فرق: {g['mandi'] - g['farmer']} روپے/کلو

✅ *کسان پکار کے ذریعے:*
آپ کو مل سکتا ہے: {g['suggested']} روپے/کلو
اضافی آمدن: +{saving} روپے/کلو

📱 *براہ راست خریدار سے ملنے کے لیے:*
"بیچنا ہے" لکھیں اور فصل کا نام بتائیں

🌾 *کسان پکار AI* 🇵🇰"""

    return f"🌾 {crop} کے ریٹ جلد اپڈیٹ ہوں گے۔"


async def get_daily_broadcast_message() -> str:
    """Daily 8AM broadcast message for all farmers"""
    today = datetime.now().strftime("%d/%m/%Y")
    day_name = ["پیر", "منگل", "بدھ", "جمعرات", "جمعہ", "ہفتہ", "اتوار"][datetime.now().weekday()]

    return f"""🌅 *کسان پکار AI — صبح کی رپورٹ*
{day_name}، {today}

*🌾 آج کی اہم باتیں:*

📊 *پشاور منڈی:*
• ٹماٹر: 80-120 روپے/کلو ⬆️
• آلو: 45-65 روپے/کلو ➡️
• پیاز: 55-80 روپے/کلو ⬇️

🌤️ *KPK موسم:*
• صبح: ٹھنڈ، دوپہر: گرم
• بارش: آج نہیں

💡 *آج کا زرعی مشورہ:*
گندم کو ابھی پانی دینے کا بہترین وقت ہے۔
صبح یا شام کو پانی دیں۔

━━━━━━━━━━━━━━━
📱 کسی بھی سوال کے لیے لکھیں
🌾 *کسان پکار — ہر قدم پر آپ کے ساتھ* 🇵🇰"""
