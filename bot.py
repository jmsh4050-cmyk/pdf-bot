import os
import telebot
import fitz
import arabic_reshaper
from bidi.algorithm import get_display
from google import genai # المكتبة الجديدة

# جلب المفاتيح
API_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_KEY")

# إعداد العميل الجديد (هذا هو الحل الجبري)
client = genai.Client(api_key=GEMINI_KEY)

bot = telebot.TeleBot(API_TOKEN)
user_data = {}

def fix_arabic(text):
    if not text: return ""
    return get_display(arabic_reshaper.reshape(text))

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, fix_arabic("أهلاً وسام! أرسل الملف الآن.. هلمرة غصباً عليه يشتغل."))

@bot.message_handler(content_types=['document'])
def handle_pdf(message):
    path = f"{message.from_user.id}.pdf"
    file_info = bot.get_file(message.document.file_id)
    with open(path, 'wb') as f:
        f.write(bot.download_file(file_info.file_path))
    user_data[message.from_user.id] = path
    
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("📝 صنع اختبار", callback_data="quiz"))
    bot.reply_to(message, fix_arabic("وصل الملف! اضغط للبدء:"), reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "quiz")
def make_quiz(call):
    uid = call.from_user.id
    bot.edit_message_text(fix_arabic("⏳ جاري التحليل بالنظام الجديد..."), call.message.chat.id, call.message.message_id)
    try:
        doc = fitz.open(user_data[uid])
        content = " ".join([page.get_text() for page in doc])
        doc.close()
        
        # الطريقة الجديدة لطلب الأسئلة (تتخطى الـ 404)
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=f"اعطني 3 أسئلة طبية خيارات بالعربي من هذا النص: {content[:3000]}"
        )
        
        bot.send_message(call.message.chat.id, fix_arabic(response.text))
    except Exception as e:
        bot.send_message(call.message.chat.id, f"Error: {str(e)}")

bot.polling(none_stop=True)
