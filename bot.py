import os
import telebot
import fitz
import arabic_reshaper
from bidi.algorithm import get_display
import google.generativeai as genai

# جلب المفاتيح من Railway
API_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_KEY")

# --- التعديل الجبري هنا ---
genai.configure(api_key=GEMINI_KEY)
# إجبار الكود على استخدام الموديل المستقر مباشرة
model = genai.GenerativeModel('gemini-1.5-flash')

bot = telebot.TeleBot(API_TOKEN)
user_data = {}

def fix_arabic(text):
    if not text: return ""
    return get_display(arabic_reshaper.reshape(text))

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, fix_arabic("أهلاً وسام! أرسل الملف الآن لصنع الاختبار."))

@bot.message_handler(content_types=['document'])
def handle_pdf(message):
    user_id = message.from_user.id
    file_info = bot.get_file(message.document.file_id)
    downloaded = bot.download_file(file_info.file_path)
    path = f"{user_id}.pdf"
    with open(path, 'wb') as f: f.write(downloaded)
    user_data[user_id] = path
    
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("📝 صنع الاختبار", callback_data="quiz"))
    bot.reply_to(message, fix_arabic("تم استلام الملف بنجاح!"), reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "quiz")
def make_quiz(call):
    uid = call.from_user.id
    bot.edit_message_text(fix_arabic("⏳ جاري التحليل بصورة مستقرة..."), call.message.chat.id, call.message.message_id)
    try:
        doc = fitz.open(user_data[uid])
        content = " ".join([page.get_text() for page in doc])
        doc.close()
        
        # طلب الأسئلة
        res = model.generate_content(f"اعطني 3 أسئلة خيارات بالعربي من هذا النص: {content[:3000]}")
        bot.send_message(call.message.chat.id, fix_arabic(res.text))
    except Exception as e:
        bot.send_message(call.message.chat.id, f"Error: {str(e)}")

bot.polling(none_stop=True)
