import os
import json
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage
from linebot.exceptions import InvalidSignatureError

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

# ==============================================


# ========= PARSE FUNCTION =========
def parse_message(text):
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

    # Clean number
    number = number.replace(",", "")

    try:
        value = float(number)
    except:
        return None

    # Format with comma
    formatted_value = "{:,.2f}".format(value)

    return item, paid_by, currency, formatted_value


# ========= WRITE TO GOOGLE SHEET =========
def append_to_sheet(item, paid_by, currency, amount):
    # Columns: A B C D E F
    row = ["", "", "", "", "", ""]  # A B C D E F

    row[0] = item        # A
    row[2] = paid_by     # C

    if currency == "KRW":
        row[3] = amount  # D
    elif currency == "THB":
        row[5] = amount  # F
    body = {
        "values": [row]
    }

    sheet.values().append(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{SHEET_NAME}!A:F",
        valueInputOption="RAW",
        body=body
    ).execute()


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
    text = event.message.text

    parsed = parse_message(text)

    if parsed:
        item, paid_by, currency, amount = parsed
        append_to_sheet(item, paid_by, currency, amount)

        # Optional: reply success
        line_bot_api.reply_message(
            event.reply_token,
            TextMessage(text=f"✅ Saved: {item} ({currency} {amount})")
        )
    else:
        # Optional: reply error
        line_bot_api.reply_message(
            event.reply_token,
            TextMessage(text="❌ Invalid format. Use: Item_PaidBy_THB/KRWAmount")
        )


# ========= MAIN =========
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)