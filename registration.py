import database

# Twilio join messages ignore karo
IGNORE_MESSAGES = [
    "join list-stream",
    "join",
    "stop",
    "start",
    "hello",
    "hi",
    "hey"
]

QUESTIONS = {
    0: """🌾 *کسان پکار AI*

السلام علیکم! 👋

کسان پکار AI شروع کرنے سے پہلے —
آپ کا نام کیا ہے؟

_(اپنا نام لکھ کر بھیجیں)_""",

    1: "✅ شکریہ!\n\n*سوال 2/4:* آپ کس صوبے یا ضلع میں ہیں؟\n_(مثال: پنجاب، سندھ، KPK، بلوچستان)_",

    2: """✅

*سوال 3/4:* آپ کون سی فصل اگاتے ہیں؟

گندم / چاول / کپاس / گنا / مکئی / سبزیاں / پھل
_(جو فصل ہو وہ لکھیں)_""",

    3: "*سوال 4/4:* آپ کی زمین کتنے ایکڑ ہے؟\n_(صرف نمبر لکھیں — مثال: 5)_"
}


async def handle_registration(text: str, phone: str):
    """
    Returns reply string if still in registration.
    Returns None if already registered → go to main chat.
    """
    user = database.get_user(phone)

    # ── Already registered → main chat pe jao ──
    if user and database.is_registered(phone):
        return None

    # ── Twilio join/stop messages ignore karo ──
    if text.strip().lower() in IGNORE_MESSAGES:
        if not user:
            database.create_user(phone)
        return QUESTIONS[0]

    # ── Brand new user ──
    if not user:
        database.create_user(phone)
        return QUESTIONS[0]

    step = database.get_reg_step(phone)

    # Step 0 → Naam
    if step == 0:
        if len(text.strip()) < 2:
            return "براہ کرم اپنا نام لکھیں 🙏"
        database.update_user(phone, {"Name": text.strip(), "reg_step": 1})
        return QUESTIONS[1]

    # Step 1 → Region
    elif step == 1:
        database.update_user(phone, {"Region": text.strip(), "reg_step": 2})
        return QUESTIONS[2]

    # Step 2 → Crop
    elif step == 2:
        database.update_user(phone, {"crop_type": text.strip(), "reg_step": 3})
        return QUESTIONS[3]

    # Step 3 → Acres → Complete!
    elif step == 3:
        try:
            acres = float(text.strip())
        except ValueError:
            acres = 0

        user_data  = database.get_user(phone)
        name = user_data.get("fields", {}).get("Name", "کسان") if user_data else "کسان"

        database.update_user(phone, {
            "land_acres": acres,
            "registered": True,
            "reg_step":   4
        })

        return f"""🎉 *رجسٹریشن مکمل!*

خوش آمدید *{name}* صاحب/صاحبہ!
آپ کسان پکار AI فیملی کا حصہ بن گئے! 🌾

اب آپ یہ کر سکتے ہیں:
📸 *تصویر بھیجیں* ← فصل کی بیماری
🎤 *آواز میں پوچھیں* ← زرعی مشورہ
💬 *لکھ کر پوچھیں* ← کوئی بھی سوال
📊 *ریٹ* لکھیں ← آج کے منڈی بھاؤ

*کسان پکار — ہر قدم پر آپ کے ساتھ* 🇵🇰"""

    return None
