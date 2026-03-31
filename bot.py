import os
import telebot
import fitz
import arabic_reshaper
from bidi.algorithm import get_display
import google.generativeai as genai

# جلب المفاتيح
API_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_KEY")

# إعداد Gemini بالنسخة المستقرة حصراً
genai.configure(api_key=GEMINI_KEY)

# --- التغيير الجذري هنا ---
# نحدد الإصدار v1 بشكل صريح داخل تعريف الموديل
model = genai.GenerativeModel(
    model_name='gemini-1.5-flash'
)

bot = telebot.TeleBot(API_TOKEN)
user_data = {}

def fix_arabic(text):
    if not text: return ""
    return get_display(arabic_reshaper.reshape(text))

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, fix_arabic("أهلاً وسام! أرسل المحاضرة PDF الآن."))

@bot.message_handler(content_types=['document'])
def handle_pdf(message):
    file_info = bot.get_file(message.document.file_id)
    downloaded = bot.download_file(file_info.file_path)
    path = f"{message.from_user.id}.pdf"
    with open(path, 'wb') as f: f.write(downloaded)
    user_data[message.from_user.id] = path
    
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("📝 صنع كويز ذكي", callback_data="quiz"))
    bot.reply_to(message, fix_arabic("وصلت المحاضرة! اضغط لبدء الاختبار:"), reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "quiz")
def make_quiz(call):
    uid = call.from_user.id
    bot.edit_message_text(fix_arabic("⏳ جاري استخراج الأسئلة..."), call.message.chat.id, call.message.message_id)
    try:
        doc = fitz.open(user_data[uid])
        content = " ".join([page.get_text() for page in doc])
        doc.close()
        
        # نستخدم generate_content مع باراميترز واضحة
        response = model.generate_content(
            f"Extract 3 medical MCQs in Arabic from this text: {content[:3000]}"
        )
        
        bot.send_message(call.message.chat.id, fix_arabic(response.text))
    except Exception as e:
        # إذا طلع خطأ، خليه يطبع التفاصيل حتى نعرف وين المشكلة بالضبط
        bot.send_message(call.message.chat.id, f"Error Detail: {str(e)}")

bot.polling(none_stop=True)
