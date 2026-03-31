import os
import telebot
import fitz  # PyMuPDF
import arabic_reshaper
from bidi.algorithm import get_display
import google.generativeai as genai

# --- جلب المفاتيح من خزنة Railway (أمان 100%) ---
API_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_KEY")
CHANNEL_USERNAME = '@W_S_B52'

# إعداد جمناي
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')

bot = telebot.TeleBot(API_TOKEN)
user_data = {}

def fix_arabic(text):
    if not text: return ""
    return get_display(arabic_reshaper.reshape(text))

def is_subscribed(user_id):
    try:
        status = bot.get_chat_member(CHANNEL_USERNAME, user_id).status
        return status in ['member', 'administrator', 'creator']
    except: return False

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, fix_arabic(f"أهلاً {message.from_user.first_name}! بوت ذكاء Gemini لطلبة التمريض جاهز."))

@bot.message_handler(content_types=['document'])
def handle_docs(message):
    user_id = message.from_user.id
    if not is_subscribed(user_id):
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("✅ اشترك بالقناة", url=f"https://t.me/{CHANNEL_USERNAME[1:]}"))
        bot.reply_to(message, fix_arabic("عذراً، اشترك بالقناة أولاً للاستمرار."), reply_markup=markup)
        return

    file_info = bot.get_file(message.document.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    file_path = f"temp_{user_id}.pdf"
    with open(file_path, 'wb') as f: f.write(downloaded_file)
    user_data[user_id] = file_path
    
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("📝 صنع اختبار ذكي", callback_data="make_quiz"))
    bot.reply_to(message, fix_arabic("تم استلام المحاضرة. اختر:"), reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "make_quiz")
def callback_quiz(call):
    user_id = call.from_user.id
    if user_id not in user_data: return
    bot.edit_message_text(fix_arabic("⏳ جاري تحليل المحاضرة..."), call.message.chat.id, call.message.message_id)
    try:
        doc = fitz.open(user_data[user_id])
        text = " ".join([page.get_text() for page in doc])
        doc.close()
        prompt = f"Extract 3 multiple choice questions in Arabic from this text: {text[:3000]}"
        response = model.generate_content(prompt)
        bot.send_message(call.message.chat.id, fix_arabic(response.text))
    except Exception as e:
        bot.send_message(call.message.chat.id, f"Error: {str(e)}")

bot.polling(none_stop=True)
