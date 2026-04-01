import os
import json
from flask import Flask, request, abort

from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

from google.oauth2 import service_account
from googleapiclient.discovery import build


# ================= ENV VARIABLES =================
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
SHEET_NAME = os.getenv("SHEET_NAME", "Sheet1")
GOOGLE_CREDENTIALS = os.getenv("GOOGLE_CREDENTIALS")
# =================================================


app = Flask(__name__)

if not LINE_CHANNEL_ACCESS_TOKEN:
    raise ValueError("LINE_CHANNEL_ACCESS_TOKEN is not set")
if not LINE_CHANNEL_SECRET:
    raise ValueError("LINE_CHANNEL_SECRET is not set")
if not GOOGLE_CREDENTIALS:
    raise ValueError("GOOGLE_CREDENTIALS is not set")
if not SPREADSHEET_ID:
    raise ValueError("SPREADSHEET_ID is not set")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# ===== GOOGLE SHEETS AUTH (FROM ENV JSON) =====
creds_dict = json.loads(GOOGLE_CREDENTIALS)

creds = service_account.Credentials.from_service_account_info(
    creds_dict,
    scopes=["https://www.googleapis.com/auth/spreadsheets"]
)

service = build("sheets", "v4", credentials=creds)
sheet = service.spreadsheets()

# ============================================================
# EMBEDDED ITINERARY DATA (from your PDF)
# ============================================================
ITINERARY = {
    1: {
        "title": "Busan",
        "route": "Gwangalli → Yeongdo (W first) → Haeundae → Cheongsapo → Hwangnyeongsan → Gwangalli",
        "activities": [
            {
                "time": "07:30 – 08:10",
                "city": "Gwangalli, Suyeong-gu",
                "activity": "Hotel bag drop",
                "notes": "",
                "status": ""
            },
            {
                "time": "09:00 – 10:30",
                "city": "Haeundae-gu",
                "activity": "Haeundae Traditional Market",
                "notes": "Haejangguk, fish cake, bungeoppang, dwaeji-gukbap",
                "status": "→ Route note"
            },
            {
                "time": "11:00 – 11:45",
                "city": "Haeundae-gu",
                "activity": "Morning café — Rendeja-Vous or Cup & Cup",
                "notes": "Jayeondo Sogeumppang (Salt Bread)",
                "status": ""
            },
            {
                "time": "12:00 – 13:00",
                "city": "Haeundae-gu",
                "activity": "Lunch",
                "notes": "",
                "status": ""
            },
            {
                "time": "13:00 – 14:30",
                "city": "Haedong Yonggungsa Temple",
                "activity": "Haedong Yonggungsa Temple",
                "notes": "",
                "status": ""
            },
            {
                "time": "15:30 – 16:30",
                "city": "Cheongsapo, Haeundae-gu",
                "activity": "Haeundae Blueline Park Sky Capsule",
                "notes": "Mipo departure 15:30 ~ 16:00",
                "status": "🔒 Fixed booking"
            },
            {
                "time": "18:00 – 19:00",
                "city": "Hwangnyeongsan, Suyeong-gu",
                "activity": "Hwangnyeongsan Observatory Sunset",
                "notes": "On the way back to Gwangalli",
                "status": ""
            },
            {
                "time": "19:30 – 20:45",
                "city": "Gwangalli, Suyeong-gu",
                "activity": "Dinner — Peace pork grill",
                "notes": "",
                "status": ""
            },
        ],
    },
    2: {
        "title": "Jinhae + Busan",
        "route": "Busan → Jinhae (SW) → Samnak on the way back → Gwangalli → Bay 101, Haeundae",
        "activities": [
            {
                "time": "~07:30",
                "city": "Seobu Terminal, Sasang-gu",
                "activity": "Depart bus → Jinhae",
                "notes": "~1 hour intercity bus",
                "status": "→ Route note"
            },
            {
                "time": "09:00 – 10:30",
                "city": "Jinhae (Gyeonghwa-dong)",
                "activity": "Gyeonghwa Station Sakura",
                "notes": "Arrive early — peak crowds",
                "status": "🔒 Fixed booking"
            },
            {
                "time": "10:45 – 12:15",
                "city": "Jinhae (Yeojwacheon)",
                "activity": "Yeojwacheon Stream",
                "notes": "1.4 km blossom canal walk",
                "status": ""
            },
            {
                "time": "12:30 – 13:30",
                "city": "Jinhae",
                "activity": "Lunch",
                "notes": "Find restaurant",
                "status": "⚠ Find restaurant"
            },
            {
                "time": "14:00 – 15:30",
                "city": "Samnak, Sasang-gu",
                "activity": "Samnak Ecological Park",
                "notes": "Naturally on the route back from Jinhae",
                "status": "→ Route note"
            },
            {
                "time": "15:30 – 16:30",
                "city": "",
                "activity": "Gaegeum Cherry Blossom Road",
                "notes": "",
                "status": ""
            },
            {
                "time": "17:30 – 18:45",
                "city": "Gwangalli, Suyeong-gu",
                "activity": "Dinner",
                "notes": "",
                "status": ""
            },
            {
                "time": "20:00 – 21:30",
                "city": "Haeundae (Bay 101)",
                "activity": "Yacht Tour",
                "notes": "Busan Yacht Tour — Bay 101, Haeundae",
                "status": ""
            },
        ],
    },
    3: {
        "title": "Busan → Seoul",
        "route": "Gwangalli → Gamcheon (W) → Dakbatgol → rest / café → Busan Station → KTX → Cheongdam, Seoul",
        "activities": [
            {
                "time": "08:30 – 10:45",
                "city": "Saha-gu (Gamcheon)",
                "activity": "Gamcheon Culture Village",
                "notes": "Little Prince Statue",
                "status": ""
            },
            {
                "time": "11:00 – 12:00",
                "city": "Nam-gu (Dakbatgol)",
                "activity": "Dakbatgol Mural Village",
                "notes": "",
                "status": ""
            },
            {
                "time": "12:15 – 13:15",
                "city": "Busan, central",
                "activity": "Lunch (Nampodong Shopping Street)",
                "notes": "Hotteok, O’Sulloc Tea house",
                "status": "⚠ Find restaurant"
            },
            {
                "time": "13:30 – 15:30",
                "city": "Busan, central",
                "activity": "Free time / café — Momos Yeongdo Roastery",
                "notes": "",
                "status": "→ Route note"
            },
            {
                "time": "17:15",
                "city": "Busan Station, Dong-gu",
                "activity": "KTX — Depart",
                "notes": "Must board on time",
                "status": "🔒 Fixed booking"
            },
            {
                "time": "19:48",
                "city": "Seoul Station, Jung-gu",
                "activity": "KTX — Arrive Seoul",
                "notes": "",
                "status": ""
            },
            {
                "time": "20:45 – 22:00",
                "city": "Cheongdam, Gangnam-gu",
                "activity": "Dinner — Haengbok Chupungnyeong Kal Samgyeopsal",
                "notes": "Reserve around 20:45",
                "status": "🔒 Fixed booking"
            },
        ],
    },
    4: {
        "title": "Seoul — Shopping",
        "route": "Seongsu → COEX / Samseong → Apgujeong / Dosan → Cheongdam (one clean south-west sweep)",
        "activities": [
            {
                "time": "08:45 – 09:30",
                "city": "Seongsu, Seongdong-gu",
                "activity": "Morning café — Human Made / Blue Bottle",
                "notes": "Blue Bottle collaboration café",
                "status": ""
            },
            {
                "time": "11:00 – 13:15",
                "city": "Seongsu, Seongdong-gu",
                "activity": "Shopping — Seongsu flagships",
                "notes": "Adidas, DIOR Silverhouse, Tamburins, HAUS, Kodak, Old Ferry",
                "status": ""
            },
            {
                "time": "13:20 – 14:15",
                "city": "Seongsu, Seongdong-gu",
                "activity": "Lunch — Kyeong Yang Katsu",
                "notes": "",
                "status": ""
            },
            {
                "time": "15:00 – 16:00",
                "city": "COEX, Samseong-dong",
                "activity": "Starfield Library",
                "notes": "Best photo op; mall open until 22:00",
                "status": ""
            },
            {
                "time": "16:30 – 19:30",
                "city": "Apgujeong / Dosan, Gangnam-gu",
                "activity": "Shopping — Apgujeong / Dosan",
                "notes": "Human Made, Emis, MARITHÉ, Stüssy, ASSC, Jayeondo (Salted Bread)",
                "status": ""
            },
            {
                "time": "19:45 – 21:00",
                "city": "Cheongdam, Gangnam-gu",
                "activity": "Dinner — Yeongdong Jang-eo & Mirak",
                "notes": "",
                "status": ""
            },
        ],
    },
    5: {
        "title": "Classic Seoul",
        "route": "Changdeokgung / Bukchon (N) → Ewha (NW — go west first!) → Gwanghwamun + Cheonggyecheon → Namsan → Myeongdong",
        "activities": [
            {
                "time": "09:00 – 11:00",
                "city": "Jongno-gu (Wonseo-dong)",
                "activity": "Changdeokgung Palace",
                "notes": "English tour 10:30 or 14:30 — book online",
                "status": "🔒 Fixed booking"
            },
            {
                "time": "11:10 – 11:40",
                "city": "Bukchon, Jongno-gu",
                "activity": "Bukchon Yukgyeong photo spot",
                "notes": "Keep noise low — residential area",
                "status": ""
            },
            {
                "time": "12:00 – 13:00",
                "city": "Anguk / Bukchon",
                "activity": "Lunch",
                "notes": "Find restaurant",
                "status": "⚠ Find restaurant"
            },
            {
                "time": "13:20 – 15:00",
                "city": "Seodaemun-gu (Sinchon)",
                "activity": "Ewha Womans University",
                "notes": "Go west before heading south — avoids backtrack",
                "status": "→ Route note"
            },
            {
                "time": "15:10 – 16:00",
                "city": "Gwanghwamun, Jongno-gu",
                "activity": "King Sejong Statue + Cheonggyecheon Stream",
                "notes": "Adjacent stops — combine on the way back",
                "status": ""
            },
            {
                "time": "16:15 – 17:20",
                "city": "Namsan, Jung-gu",
                "activity": "Namsan Baekbeom Square",
                "notes": "Base of Namsan mountain",
                "status": ""
            },
            {
                "time": "17:30 – 19:30",
                "city": "Namsan, Yongsan-gu",
                "activity": "N Seoul Tower",
                "notes": "Sunset → night view; cable car or walk",
                "status": ""
            },
            {
                "time": "19:30 – 20:00",
                "city": "Myeongdong, Jung-gu",
                "activity": "Myeongdong Night Market",
                "notes": "Street food + shopping",
                "status": ""
            },
            {
                "time": "20:00 – 21:00",
                "city": "Myeongdong, Jung-gu",
                "activity": "Dinner",
                "notes": "Find restaurant",
                "status": "⚠ Find restaurant"
            },
        ],
    },
    6: {
        "title": "Farewell + Fly",
        "route": "Gyeongbokgung (N Jongno) → Gwangjang Market (E Jongno, 5 min away) → Seokchon Lake (Jamsil, SE) → hotel → ICN",
        "activities": [
            {
                "time": "09:00 – 10:45",
                "city": "Gyeongbokgung, Jongno-gu",
                "activity": "Gyeongbokgung Palace",
                "notes": "Guard ceremony 10:00 & 14:00",
                "status": ""
            },
            {
                "time": "11:00 – 12:15",
                "city": "Gwangjang Market, Jongno-gu",
                "activity": "Lunch — Gwangjang Market",
                "notes": "Bindaetteok, mayak kimbap, yukhoe, cash preferred",
                "status": ""
            },
            {
                "time": "13:15 – 15:00",
                "city": "Seokchon Lake, Jamsil (Songpa-gu)",
                "activity": "Seokchon Lake Park",
                "notes": "Cherry blossoms; free entry",
                "status": ""
            },
            {
                "time": "15:30",
                "city": "Hotel (Cheongdam)",
                "activity": "Return hotel — collect luggage",
                "notes": "Depart by 16:00 – 16:30 at the latest",
                "status": "🔒 Fixed booking"
            },
            {
                "time": "17:00 – 18:00",
                "city": "ICN Airport",
                "activity": "Early dinner",
                "notes": "",
                "status": ""
            },
            {
                "time": "19:35",
                "city": "ICN Terminal 1",
                "activity": "Departure ✈",
                "notes": "",
                "status": ""
            },
        ],
    },
}
# ============================================================


def parse_expense_message(text):
    """
    Old format:
    Item_PaidBy_THB1000
    Item_PaidBy_KRW1000
    """
    parts = text.strip().split("_")

    # Must be exactly 3 parts
    if len(parts) != 3:
        return None

    item = parts[0].strip()
    paid_by = parts[1].strip()
    amount_raw = parts[2].strip()

    # Detect currency
    if amount_raw.startswith("THB"):
        currency = "THB"
        number = amount_raw.replace("THB", "")
    elif amount_raw.startswith("KRW"):
        currency = "KRW"
        number = amount_raw.replace("KRW", "")
    else:
        return None

    number = number.replace(",", "")

    try:
        value = float(number)
    except ValueError:
        return None

    formatted_value = "{:,.2f}".format(value)
    return item, paid_by, currency, formatted_value


def append_to_sheet(item, paid_by, currency, amount):
    """
    Writes to the Google Sheet in the same way as your old code.
    Columns: A B C D E F
    """
    row = ["", "", "", "", "", ""]  # A B C D E F

    row[0] = item    # A
    row[2] = paid_by # C

    if currency == "KRW":
        row[3] = amount  # D
    elif currency == "THB":
        row[5] = amount  # F

    body = {"values": [row]}

    sheet.values().append(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{SHEET_NAME}!A1",
        valueInputOption="RAW",
        body=body
    ).execute()


def get_emoji(activity_text, notes_text=""):
    text = f"{activity_text} {notes_text}".lower()

    if "café" in text or "cafe" in text:
        return "☕"
    if "lunch" in text or "dinner" in text:
        return "🍽️"
    if "shopping" in text:
        return "🛍️"
    if "market" in text:
        return "🛒"
    if "palace" in text or "temple" in text or "shrine" in text:
        return "🏯"
    if "university" in text:
        return "🎓"
    if "station" in text or "ktx" in text or "bus" in text or "airport" in text:
        return "🚆"
    if "lake" in text or "park" in text or "stream" in text or "observatory" in text:
        return "🌿"
    if "departure" in text or "depart" in text:
        return "✈️"
    return "📍"


def format_single_activity(day_num, activity_num):
    day_data = ITINERARY.get(day_num)
    if not day_data:
        return f"❌ Day {day_num} not found."

    activities = day_data["activities"]
    if activity_num < 1 or activity_num > len(activities):
        return f"❌ Activity {activity_num} not found for Day {day_num}."

    a = activities[activity_num - 1]
    emoji = get_emoji(a["activity"], a["notes"])

    msg = [
        f"🗓️ Day {day_num} — Activity {activity_num}",
        f"🏷️ {day_data['title']}",
        "",
        f"{emoji} {a['activity']}",
        f"⏰ {a['time']}",
    ]

    if a["city"]:
        msg.append(f"📍 {a['city']}")
    if a["notes"]:
        msg.append(f"📝 {a['notes']}")
    if a["status"]:
        msg.append(f"{a['status']}")

    return "\n".join(msg)


def format_full_day(day_num):
    day_data = ITINERARY.get(day_num)
    if not day_data:
        return f"❌ Day {day_num} not found."

    lines = [
        f"🇰🇷 Day {day_num} — {day_data['title']}",
        f"🛣️ Route: {day_data['route']}",
        ""
    ]

    for idx, a in enumerate(day_data["activities"], start=1):
        emoji = get_emoji(a["activity"], a["notes"])
        lines.append(f"{idx}️⃣ {emoji} {a['activity']}")
        lines.append(f"⏰ {a['time']}")
        if a["city"]:
            lines.append(f"📍 {a['city']}")
        if a["notes"]:
            lines.append(f"📝 {a['notes']}")
        if a["status"]:
            lines.append(f"{a['status']}")
        lines.append("")  # blank line between activities

    return "\n".join(lines).strip()


def handle_itinerary_command(text):
    """
    Supported:
    itinerary_1      -> full day 1
    itinerary_1_1    -> activity 1 of day 1
    """
    parts = text.strip().split("_")

    if len(parts) == 2:
        # itinerary_1
        if parts[1].isdigit():
            day_num = int(parts[1])
            return format_full_day(day_num)
        return "❌ Invalid itinerary format. Use: itinerary_1 or itinerary_1_1"

    if len(parts) == 3:
        # itinerary_1_1
        if parts[1].isdigit() and parts[2].isdigit():
            day_num = int(parts[1])
            activity_num = int(parts[2])
            return format_single_activity(day_num, activity_num)
        return "❌ Invalid itinerary format. Use: itinerary_1 or itinerary_1_1"

    return "❌ Invalid itinerary format. Use: itinerary_1 or itinerary_1_1"


# ========= LINE WEBHOOK =========
@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature")
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK"


# ========= HANDLE MESSAGE =========
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text.strip()

    # 1) ITINERARY COMMANDS FIRST
    if text.lower().startswith("itinerary"):
        reply = handle_itinerary_command(text)
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply)
        )
        return

    # 2) OLD EXPENSE PARSER
    parsed = parse_expense_message(text)

    if parsed:
        item, paid_by, currency, amount = parsed
        append_to_sheet(item, paid_by, currency, amount)

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"✅ Saved: {item} ({currency} {amount})")
        )
    else:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text="❌ Invalid format.\n\nExpense: Item_PaidBy_THB1000\nItinerary: itinerary_1 or itinerary_1_1"
            )
        )


# ========= MAIN =========
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
