import os
import json
from flask import Flask, request, abort

from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent,
    TextMessage,
    TextSendMessage,
    RichMenu,
    RichMenuArea,
    RichMenuBounds,
    MessageAction,
    URIAction
)

from google.oauth2 import service_account
from googleapiclient.discovery import build


# ================= ENV VARIABLES =================
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
SHEET_NAME = os.getenv("SHEET_NAME", "Sheet1")
GOOGLE_CREDENTIALS = os.getenv("GOOGLE_CREDENTIALS")

# Render URL for wake button
BASE_URL = os.getenv("RENDER_EXTERNAL_URL")

# =================================================

app = Flask(__name__)

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)


# ===== GOOGLE SHEETS AUTH =====
creds_dict = json.loads(GOOGLE_CREDENTIALS)

creds = service_account.Credentials.from_service_account_info(
    creds_dict,
    scopes=["https://www.googleapis.com/auth/spreadsheets"]
)

service = build("sheets", "v4", credentials=creds)
sheet = service.spreadsheets()


# =================================================
# WAKE ENDPOINT
# =================================================

@app.route("/")
def home():
    return "LINE Travel Bot Running 🚀"

@app.route("/wake")
def wake():
    return "Bot is awake 🚀"


# =================================================
# ITINERARY DATA (Embedded)
# =================================================

ITINERARY = {
    1: {
        "title": "Busan",
        "activities": [
            ("07:30 – 08:10", "Hotel bag drop", "Gwangalli"),
            ("09:00 – 10:30", "Haeundae Traditional Market", "Haeundae"),
            ("11:00 – 11:45", "Morning café", "Haeundae"),
            ("12:00 – 13:00", "Lunch", "Haeundae"),
            ("13:00 – 14:30", "Haedong Yonggungsa Temple", "Busan"),
            ("15:30 – 16:30", "Sky Capsule", "Cheongsapo"),
            ("18:00 – 19:00", "Hwangnyeongsan Observatory", "Busan"),
            ("19:30 – 20:45", "Dinner – Peace Pork Grill", "Gwangalli"),
        ],
    },

    2: {
        "title": "Jinhae Sakura",
        "activities": [
            ("07:30", "Bus to Jinhae", "Sasang"),
            ("09:00 – 10:30", "Gyeonghwa Station Sakura", "Jinhae"),
            ("10:45 – 12:15", "Yeojwacheon Stream Walk", "Jinhae"),
            ("12:30 – 13:30", "Lunch", "Jinhae"),
            ("14:00 – 15:30", "Samnak Ecological Park", "Busan"),
            ("15:30 – 16:30", "Cherry Blossom Road", "Busan"),
            ("17:30 – 18:45", "Dinner", "Gwangalli"),
            ("20:00 – 21:30", "Yacht Tour", "Haeundae"),
        ],
    },

    3: {
        "title": "Busan → Seoul",
        "activities": [
            ("08:30 – 10:45", "Gamcheon Culture Village", "Busan"),
            ("11:00 – 12:00", "Dakbatgol Mural Village", "Busan"),
            ("12:15 – 13:15", "Lunch", "Nampo"),
            ("13:30 – 15:30", "Cafe / Free time", "Busan"),
            ("17:15", "KTX Train Depart", "Busan Station"),
            ("19:48", "Arrive Seoul", "Seoul Station"),
            ("20:45 – 22:00", "Dinner – Samgyeopsal", "Cheongdam"),
        ],
    },

    4: {
        "title": "Seoul Shopping",
        "activities": [
            ("08:45 – 09:30", "Morning café", "Seongsu"),
            ("11:00 – 13:15", "Shopping – Flagships", "Seongsu"),
            ("13:20 – 14:15", "Lunch", "Seongsu"),
            ("15:00 – 16:00", "Starfield Library", "COEX"),
            ("16:30 – 19:30", "Apgujeong Shopping", "Dosan"),
            ("19:45 – 21:00", "Dinner", "Cheongdam"),
        ],
    },

    5: {
        "title": "Classic Seoul",
        "activities": [
            ("09:00 – 11:00", "Changdeokgung Palace", "Jongno"),
            ("11:10 – 11:40", "Bukchon Hanok Village", "Bukchon"),
            ("12:00 – 13:00", "Lunch", "Anguk"),
            ("13:20 – 15:00", "Ewha University", "Sinchon"),
            ("15:10 – 16:00", "King Sejong Statue", "Gwanghwamun"),
            ("16:15 – 17:20", "Namsan Park", "Seoul"),
            ("17:30 – 19:30", "N Seoul Tower", "Namsan"),
            ("19:30 – 20:00", "Myeongdong Market", "Myeongdong"),
        ],
    },

    6: {
        "title": "Fly Home",
        "activities": [
            ("09:00 – 10:45", "Gyeongbokgung Palace", "Seoul"),
            ("11:00 – 12:15", "Gwangjang Market Lunch", "Seoul"),
            ("13:15 – 15:00", "Seokchon Lake", "Seoul"),
            ("15:30", "Return Hotel", "Cheongdam"),
            ("17:00 – 18:00", "Airport Dinner", "ICN"),
            ("19:35", "Flight Departure ✈", "ICN"),
        ],
    },
}


# =================================================
# ITINERARY FUNCTIONS
# =================================================

def get_day(day):
    if day not in ITINERARY:
        return "❌ Day not found"

    msg = f"🇰🇷 Day {day} – {ITINERARY[day]['title']}\n\n"

    for i, act in enumerate(ITINERARY[day]["activities"], start=1):
        time, activity, place = act
        msg += f"{i}️⃣ ⏰ {time}\n📍 {activity} ({place})\n\n"

    return msg


def get_activity(day, activity):
    if day not in ITINERARY:
        return "❌ Day not found"

    acts = ITINERARY[day]["activities"]

    if activity > len(acts):
        return "❌ Activity not found"

    time, act, place = acts[activity - 1]

    return f"""
📍 Day {day} Activity {activity}

⏰ {time}
🧭 {act}
📍 {place}
"""


# =================================================
# EXPENSE PARSER
# =================================================

def parse_message(text):

    parts = text.strip().split("_")

    if len(parts) != 3:
        return None

    item = parts[0]
    paid_by = parts[1]
    amount_raw = parts[2]

    if amount_raw.startswith("THB"):
        currency = "THB"
        number = amount_raw.replace("THB", "")
    elif amount_raw.startswith("KRW"):
        currency = "KRW"
        number = amount_raw.replace("KRW", "")
    else:
        return None

    try:
        value = float(number)
    except:
        return None

    formatted = "{:,.2f}".format(value)

    return item, paid_by, currency, formatted


def append_to_sheet(item, paid_by, currency, amount):

    row = ["", "", "", "", "", ""]

    row[0] = item
    row[2] = paid_by

    if currency == "KRW":
        row[3] = amount
    else:
        row[5] = amount

    body = {"values": [row]}

    sheet.values().append(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{SHEET_NAME}!A1",
        valueInputOption="RAW",
        body=body
    ).execute()


# =================================================
# LINE CALLBACK
# =================================================

@app.route("/callback", methods=["POST"])
def callback():

    signature = request.headers.get("X-Line-Signature")
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK"


# =================================================
# HANDLE MESSAGE
# =================================================

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):

    text = event.message.text

    if text.startswith("itinerary"):

        parts = text.split("_")

        if len(parts) == 2:
            reply = get_day(int(parts[1]))

        elif len(parts) == 3:
            reply = get_activity(int(parts[1]), int(parts[2]))

        else:
            reply = "Usage: itinerary_1 or itinerary_1_2"

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply)
        )

        return


    parsed = parse_message(text)

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
            TextSendMessage(text="❌ Invalid format")
        )


# =================================================
# CREATE RICH MENU (Wake + Itinerary)
# =================================================

def create_rich_menu():

    rich_menu = RichMenu(
        size={"width": 2500, "height": 843},
        selected=True,
        name="Travel Menu",
        chat_bar_text="Travel Menu",
        areas=[
            RichMenuArea(
                bounds=RichMenuBounds(x=0, y=0, width=833, height=843),
                action=URIAction(
                    label="Wake Bot",
                    uri=f"{BASE_URL}/wake"
                )
            ),
            RichMenuArea(
                bounds=RichMenuBounds(x=833, y=0, width=833, height=843),
                action=MessageAction(
                    label="Day 1",
                    text="itinerary_1"
                )
            ),
            RichMenuArea(
                bounds=RichMenuBounds(x=1666, y=0, width=833, height=843),
                action=MessageAction(
                    label="Day 2",
                    text="itinerary_2"
                )
            ),
        ]
    )

    rich_menu_id = line_bot_api.create_rich_menu(rich_menu)

    line_bot_api.set_default_rich_menu(rich_menu_id)


# =================================================
# MAIN
# =================================================

if __name__ == "__main__":

    try:
        create_rich_menu()
    except:
        pass

    port = int(os.environ.get("PORT", 5000))

    app.run(host="0.0.0.0", port=port)
