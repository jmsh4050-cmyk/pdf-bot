import os
import telebot
import fitz  # PyMuPDF
import arabic_reshaper
from bidi.algorithm import get_display
import google.generativeai as genai

# جلب المفاتيح من Railway
API_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_KEY")

# الحل الجبري لاتصال Gemini
genai.configure(api_key=GEMINI_KEY)
# إجبار النظام على استخدام موديل Flash المستقر
model = genai.GenerativeModel('gemini-1.5-flash')

bot = telebot.TeleBot(API_TOKEN)
user_data = {}

def fix_arabic(text):
    if not text: return ""
    return get_display(arabic_reshaper.reshape(text))

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, fix_arabic("أرسل الملف PDF الحين لعمل الاختبار."))

@bot.message_handler(content_types=['document'])
def handle_pdf(message):
    file_info = bot.get_file(message.document.file_id)
    downloaded = bot.download_file(file_info.file_path)
    path = f"{message.from_user.id}.pdf"
    with open(path, 'wb') as f: f.write(downloaded)
    user_data[message.from_user.id] = path
    
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("📝 صنع الاختبار", callback_data="quiz"))
    bot.reply_to(message, fix_arabic("تم! اضغط لبدء الاختبار:"), reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "quiz")
def make_quiz(call):
    uid = call.from_user.id
    bot.edit_message_text(fix_arabic("⏳ جاري التحليل..."), call.message.chat.id, call.message.message_id)
    try:
        doc = fitz.open(user_data[uid])
        content = " ".join([page.get_text() for page in doc])
        doc.close()
        
        # طلب الأسئلة
        res = model.generate_content(f"اعطني 3 أسئلة خيارات بالعربي من هذا النص: {content[:3000]}")
        bot.send_message(call.message.chat.id, fix_arabic(res.text))
    except Exception as e:
        bot.send_message(call.message.chat.id, f"خطأ: {str(e)}")

bot.polling(none_stop=True)
