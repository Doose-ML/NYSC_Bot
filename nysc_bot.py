import os
from datetime import datetime
from typing import Dict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
import firebase_admin
from firebase_admin import credentials, db
from dotenv import load_dotenv
from fuzzywuzzy import fuzz
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from apscheduler.schedulers.background import BackgroundScheduler
import asyncio
from flask import Flask
from threading import Thread

# --- Configuration ---
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
FIREBASE_DB_URL = os.getenv("FIREBASE_DB_URL")
GSHEET_ID = os.getenv("GSHEET_ID")

# --- Keep Alive Server ---
def keep_alive():
    """Creates a Flask server to keep the bot alive on Replit"""
    app = Flask(__name__)
    
    @app.route('/')
    def home():
        return "NYSC Bot is running!"
    
    def run():
        app.run(host='0.0.0.0', port=8080)
    
    Thread(target=run).start()

# --- Firebase Setup ---
# US Database Setup (MUST use this exact format)
FIREBASE_DB_URL =FIREBASE_DB_URL = os.getenv("FIREBASE_DB_URL")  

cred = credentials.Certificate("nysc-bot-firebase-adminsdk-fbsvc-3e6d43533b.json")

try:
    # Step 1: Initialize without auth override
    firebase_admin.initialize_app(cred, {
        'databaseURL': FIREBASE_DB_URL
    })
    
    # Step 2: Test with simple write
    db.reference('test').set({"us_database": True})
    
    # Step 3: Now add auth
    firebase_admin.initialize_app(cred, {
        'databaseURL': FIREBASE_DB_URL,
        'databaseAuthVariableOverride': {
            'uid': 'nysc-bot-server'
        }
    }, name='nysc-bot')  # Named app avoids duplicate init
    
    print("🔥 US Database Verified!")
    
except Exception as e:
    print(f"❌ Final 404 Fix Failed: {e}")
    print("Nuclear Option:")
    print("1. Go to Firebase Console")
    print("2. Create NEW Realtime Database in us-central1")
    print("3. Update URL to https://nysc-bot-default-rtdb.firebaseio.com/")
    exit(1)
faq_ref = db.reference('faqs')
unanswered_ref = db.reference('unanswered_questions')

# --- Google Sheets Setup ---
def init_gsheets():
    scope = ['https://spreadsheets.google.com/feeds']
    creds = ServiceAccountCredentials.from_json_keyfile_name('Google auth.json', scope)
    return gspread.authorize(creds)

# --- FAQ Database ---
nysc_faqs = {}

# --- Instant Responses ---
INSTANT_RESPONSES: Dict[str, str] = {
    "call up letter": "📄 To print your call-up letter:\n1. Visit https://portal.nysc.org.ng\n2. Login with your credentials\n3. Click 'Print Call-Up Letter' under dashboard",
    "allowance": "💰 Allowances are paid monthly between 25th-30th. Contact your LG inspector if delayed beyond 5 working days.",
    "camp requirements": "🎒 Essential camp items:\n- Original credentials\n- White shorts/vest\n- Medical certificate\n- 4 passport photographs\n- Call-up letter printout",
    "redeployment": "🔄 Redeployment Process:\n1. Submit application to LGI\n2. Provide valid reasons (health, security, marriage)\n3. Wait for approval\nNote: Must be done within first 3 weeks",
    "portal": "🌐 NYSC Portal: https://portal.nysc.org.ng\nForgot password? Use 'Recover Password' option with registered email",
    
    "registration requirements": "📝 Camp registration requires:\n- Original credentials\n- Call-up letter\n- Medical certificate\n- 4 passport photos\n- Bank verification details\n- COVID-19 vaccination card (if available)",
    "forgot portal password": "🔑 Reset your NYSC portal password:\n1. Go to https://portal.nysc.org.ng\n2. Click 'Forgot Password'\n3. Enter your registered email\n4. Check email for reset link",
    
    # Camp Essentials
    "what to bring to camp": "🎒 Essential camp items:\n- White shorts/vest (5 pairs)\n- White tennis shoes\n- Bucket and toiletries\n- Mosquito net\n- Padlock\n- Small power bank\n- Writing materials\n- Plain white round-neck T-shirts",
    "prohibited items": "🚫 Prohibited items in camp:\n- Weapons of any kind\n- Drugs/alcohol\n- Large electronics\n- Power banks >20,000mAh\n- Revealing clothing\n- Expensive jewelry",
    "dress code": "👕 Camp dress code:\n- Males: White shorts, white vest, white socks/shoes\n- Females: White shorts, white round-neck T-shirt\n- No sagging, no revealing outfits\n- No colored clothing during morning drills",
    
    # Accommodation
    "camp accommodation": "🏠 Camp accommodation:\n- Hostels are provided\n- Bring bedsheet and pillow\n- Mosquito net is essential\n- Rooms are gender-separated\n- No special treatment requests",
    "can i stay outside camp": "🏨 Staying outside camp:\n- Not allowed during orientation\n- Must sleep in assigned hostels\n- Only special medical cases may be considered\n- Requires approval from camp officials",
    
    # Allowances and Payments
    "allowance": "💰 Allowance details:\n- Monthly allowance: ₦77,000\n- Paid between 25th-30th each month\n- First payment comes after documentation\n- Paid to your NYSC bank account",
    "when will i get paid": "💵 Payment timeline:\n- First payment: 4-6 weeks after camp\n- Subsequent payments: Monthly\n- Delays? Contact your LG inspector\n- Ensure your account details are correct",
    
    # Camp Activities
    "daily schedule": "⏰ Typical camp day:\n5:30am - Morning drill\n7:30am - Breakfast\n8:30am - Lectures\n12pm - Lunch\n2pm - SAED training\n4pm - Sports\n6pm - Evening parade\n9pm - Lights out",
    "saed program": "💼 SAED Programs:\n1. Agriculture\n2. ICT\n3. Cosmetology\n4. Film Making\n5. Photography\n6. Fashion Design\nChoose one during registration",
    
    # Health and Safety
    "camp clinic": "🏥 Camp clinic services:\n- Basic medical care available\n- Bring personal medications\n- Emergency cases referred out\n- COVID-19 protocols enforced\n- First aid available 24/7",
    "security in camp": "👮 Camp security:\n- Military personnel present\n- No unauthorized exits\n- Curfew strictly enforced\n- Report incidents immediately\n- No visitors allowed in hostels",
    
    # Post-Camp
    "ppa posting": "🏢 PPA Posting:\n- Assigned during camp\n- Can be changed within 2 weeks\n- Requires valid reasons\n- Submit request to LGI\n- No guarantee of approval",
    "redeployment": "🔄 Redeployment Process:\n1. Submit application to LGI\n2. Provide valid reasons (health, security, marriage)\n3. Wait for approval\nNote: Must be done within first 3 weeks",
    
    # Miscellaneous
    "can i use phone in camp": "📱 Phone usage:\n- Allowed during free time\n- No phones during drills/lectures\n- Bring power banks (≤20,000mAh)\n- Charging ports limited",
    "visitors policy": "👪 Visitor rules:\n- No visitors in hostels\n- Can meet at camp gate\n- Visiting hours: 4pm-6pm\n- Must show ID\n- No overnight stays",
    "how long is camp": "⏳ Camp duration:\n- Orientation lasts 3 weeks\n- Strictly residential\n- No early departure allowed\n- Certificate issued at end",
    "what is mammy market": "🛒 Mammy Market:\n- Camp shopping area\n- Sells food, snacks, toiletries\n- Open after daily activities\n- Prices slightly higher\n- No alcohol sold"
}

# --- FAQ Auto-Population ---
async def load_initial_faqs():
    try:
        gc = init_gsheets()
        sheet = gc.open_by_key(GSHEET_ID).sheet1
        
        if len(sheet.get_all_values()) <= 1:  # Only headers exist
            faqs = [
                ["How do I print my call-up letter?", "Login to NYSC portal → 'Print Call-up Letter'", "pre-mobilization"],
                ["What's prohibited in camp?", "Weapons, drugs, alcohol (>20,000mAh power banks)", "camp-rules"],
                ["When is allowance paid?", "Between 25th-30th each month", "allowances"],
                ["How do I redeploy?", "Submit application to LGI with valid reasons", "posting"]
            ]
            sheet.insert_rows(faqs, row=2)
            print(f"🚀 Loaded {len(faqs)} FAQs to Google Sheets")
    except Exception as e:
        print(f"⚠️ FAQ population failed: {e}")

# --- FAQ Auto-Updater ---
async def update_faqs(context: ContextTypes.DEFAULT_TYPE):
    try:
        gc = init_gsheets()
        sheet = gc.open_by_key(GSHEET_ID).sheet1
        records = sheet.get_all_records()
        
        global nysc_faqs
        nysc_faqs = {row['Question'].lower(): row['Answer'] for row in records}
        faq_ref.set(nysc_faqs)
        
        print(f"🔄 Updated {len(nysc_faqs)} FAQs at {datetime.now()}")
    except Exception as e:
        print(f"⚠️ FAQ update failed: {e}")

# --- Bot Commands ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📅 Calendar", callback_data='calendar'),
         InlineKeyboardButton("📝 Registration", callback_data='registration')],
        [InlineKeyboardButton("🔔 Subscribe", callback_data='subscribe')]
    ]
    await update.message.reply_text(
        "🎖️ *NYSC Helper Bot*\nAsk me anything about NYSC!",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.lower()
    
    # 1. Check instant responses first
    for keyword, response in INSTANT_RESPONSES.items():
        if keyword in user_input:
            await update.message.reply_text(response, parse_mode="Markdown")
            return
    
    # 2. Check exact matches in FAQs
    for question, answer in nysc_faqs.items():
        if question in user_input:
            await update.message.reply_text(answer, parse_mode="Markdown")
            return
    
    # 3. Fuzzy matching
    best_match, highest_score = None, 0
    for question in nysc_faqs.keys():
        score = fuzz.ratio(user_input, question)
        if score > 75 and score > highest_score:
            best_match, highest_score = question, score
    
    if best_match:
        await update.message.reply_text(
            f"🔍 Did you mean:\n\n*{best_match}?*\n\n{nysc_faqs[best_match]}",
            parse_mode="Markdown"
        )
    else:
        await log_unknown_question(update, context)

async def log_unknown_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_ref = unanswered_ref.push()
    new_ref.set({
        'question': update.message.text,
        'chat_id': str(update.message.chat_id),
        'timestamp': datetime.now().isoformat(),
        'answered': False
    })
    
    await context.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=f"❓ *New Question:*\n\n{update.message.text}\n\nReply with:\n/answer {new_ref.key} [response]",
        parse_mode="Markdown"
    )
    
    await update.message.reply_text("📬 Question logged. You'll be notified when answered!")

async def answer_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.message.chat_id) != ADMIN_CHAT_ID:
        return
    
    try:
        question_id = context.args[0]
        answer = " ".join(context.args[1:])
        
        # Update Firebase
        unanswered_ref.child(question_id).update({'answered': True, 'answer': answer})
        
        # Add to FAQs
        question = unanswered_ref.child(question_id).get()['question']
        nysc_faqs[question.lower()] = answer
        faq_ref.child(question.lower()).set(answer)
        
        # Update Google Sheets
        gc = init_gsheets()
        gc.open_by_key(GSHEET_ID).sheet1.append_row([question, answer, "user-added", datetime.now().date()])
        
        # Notify user
        await context.bot.send_message(
            chat_id=unanswered_ref.child(question_id).get()['chat_id'],
            text=f"📬 *Answer to your question:*\n\n{question}\n\n{answer}",
            parse_mode="Markdown"
        )
        
        await update.message.reply_text("✅ Answer added to FAQs!")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

# --- Main ---
def main():
    # Start the keep-alive server
    keep_alive()
    
    # Create Application
    application = Application.builder().token(TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("answer", answer_question))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Initialize FAQ system
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("✅ Message handler registered")
    
    # Schedule FAQ updates every 6 hours
    scheduler = BackgroundScheduler()
    scheduler.add_job(update_faqs, 'interval', hours=6, args=[None])
    scheduler.start()
    
    # Initial FAQ load
    asyncio.get_event_loop().run_until_complete(load_initial_faqs())
    asyncio.get_event_loop().run_until_complete(update_faqs(None))
    
    print("🔄 Scheduled FAQ updates initialized")
    application.run_polling()

if __name__ == '__main__':
    main()