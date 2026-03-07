import os
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

AIRTABLE_TOKEN   = os.getenv("AIRTABLE_TOKEN")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")

HEADERS = {
    "Authorization": f"Bearer {AIRTABLE_TOKEN}",
    "Content-Type": "application/json"
}

# ⚠️ Table URLs
USERS_URL     = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/Users"
MESSAGES_URL  = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/Messages"
COMPANIES_URL = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/Companies"


# ─── USER FUNCTIONS ───────────────────────────────────────

def get_user(phone: str):
    """Phone number se user dhundo"""
    params = {"filterByFormula": f"{{Phone}}='{phone}'"}
    r = requests.get(USERS_URL, headers=HEADERS, params=params)
    records = r.json().get("records", [])
    return records[0] if records else None


def create_user(phone: str):
    """Naya user banao"""
    payload = {"records": [{"fields": {
        "Phone":      phone,
        "Language":   "urdu",
        "reg_step":   0,
        "registered": False,
        "Created At": datetime.now().strftime("%Y-%m-%d")
    }}]}
    requests.post(USERS_URL, headers=HEADERS, json=payload)


def update_user(phone: str, fields: dict):
    """User ki info update karo"""
    user = get_user(phone)
    if not user:
        return
    requests.patch(
        f"{USERS_URL}/{user['id']}",
        headers=HEADERS,
        json={"fields": fields}
    )


def get_reg_step(phone: str) -> int:
    user = get_user(phone)
    if not user:
        return -1
    return int(user.get("fields", {}).get("reg_step", 0))


def is_registered(phone: str) -> bool:
    user = get_user(phone)
    if not user:
        return False
    return bool(user.get("fields", {}).get("registered", False))


# ─── MESSAGE FUNCTIONS ────────────────────────────────────

def save_message(phone: str, msg_type: str, user_msg: str, bot_reply: str):
    """Message history save karo"""
    payload = {"records": [{"fields": {
        "phone_number": phone,
        "message_type": msg_type,
        "user_message": (user_msg or "")[:500],
        "bot_reply":    (bot_reply or "")[:500],
        "created_at":   datetime.now().isoformat()
    }}]}
    try:
        requests.post(MESSAGES_URL, headers=HEADERS, json=payload)
    except Exception as e:
        print(f"Message save error: {e}")


# ─── COMPANIES FUNCTIONS ──────────────────────────────────

def get_companies(limit: int = 100):
    """Sab companies dhundo"""
    params = {"maxRecords": limit}
    r = requests.get(COMPANIES_URL, headers=HEADERS, params=params)
    return r.json().get("records", [])


def create_company(name: str, company_type: str, contact: str, region: str, products: str, plan: str):
    """Nai company add karo"""
    payload = {"records": [{"fields": {
        "company_name": name,
        "company_type": company_type,
        "contact":      contact,
        "region":       region,
        "products":     products,
        "plan":         plan,
        "active":       True,
        "created_at":   datetime.now().isoformat()
    }}]}
    r = requests.post(COMPANIES_URL, headers=HEADERS, json=payload)
    return r.json()


# ─── DASHBOARD STATS ──────────────────────────────────────

def get_dashboard_stats() -> dict:
    """Admin dashboard ke liye stats"""

    # Users fetch
    u_resp = requests.get(USERS_URL, headers=HEADERS, params={
        "fields[]": ["Phone", "registered", "Region", "crop_type", "Language"]
    })
    all_users = u_resp.json().get("records", [])

    region_count = {}
    crop_count   = {}
    lang_count   = {}
    registered   = 0

    for u in all_users:
        f = u.get("fields", {})
        if f.get("registered"):
            registered += 1
        region = f.get("Region", "نامعلوم")
        crop   = f.get("crop_type", "نامعلوم")
        lang   = f.get("Language", "urdu")
        region_count[region] = region_count.get(region, 0) + 1
        crop_count[crop]     = crop_count.get(crop, 0) + 1
        lang_count[lang]     = lang_count.get(lang, 0) + 1

    # Messages fetch
    m_resp = requests.get(MESSAGES_URL, headers=HEADERS, params={
        "fields[]": ["message_type"]
    })
    all_msgs = m_resp.json().get("records", [])

    type_count = {"text": 0, "image": 0, "voice": 0}
    for m in all_msgs:
        t = m.get("fields", {}).get("message_type", "text")
        type_count[t] = type_count.get(t, 0) + 1

    return {
        "total_users":      len(all_users),
        "registered_users": registered,
        "total_messages":   len(all_msgs),
        "region_breakdown": dict(sorted(region_count.items(), key=lambda x: -x[1])),
        "crop_breakdown":   dict(sorted(crop_count.items(), key=lambda x: -x[1])),
        "lang_breakdown":   lang_count,
        "message_types":    type_count,
        "top_region": max(region_count, key=region_count.get) if region_count else "N/A",
        "top_crop":   max(crop_count,   key=crop_count.get)   if crop_count   else "N/A",
    }
