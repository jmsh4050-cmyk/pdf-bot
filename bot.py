import os
import telebot
import fitz  # PyMuPDF
import arabic_reshaper
from bidi.algorithm import get_display
import google.generativeai as genai

# --- جلب المفاتيح من Railway ---
API_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_KEY")

# إعداد Gemini (هذا الجزء يحل مشكلة 404)
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(model_name="gemini-1.5-flash")

bot = telebot.TeleBot(API_TOKEN)
user_data = {}

def fix_arabic(text):
    if not text: return ""
    # تصحيح الحروف العربية وعكس الاتجاه
    reshaped_text = arabic_reshaper.reshape(text)
    return get_display(reshaped_text)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, fix_arabic("أهلاً! أرسل ملف PDF وسأقوم بصنع اختبار ذكي لك."))

@bot.message_handler(content_types=['document'])
def handle_docs(message):
    user_id = message.from_user.id
    file_info = bot.get_file(message.document.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    file_path = f"temp_{user_id}.pdf"
    
    with open(file_path, 'wb') as f:
        f.write(downloaded_file)
    
    user_data[user_id] = file_path
    
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("📝 ابدأ الاختبار", callback_data="make_quiz"))
    bot.reply_to(message, fix_arabic("تم استلام الملف!"), reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "make_quiz")
def callback_quiz(call):
    user_id = call.from_user.id
    if user_id not in user_data: return

    bot.edit_message_text(fix_arabic("⏳ جاري صنع الأسئلة..."), call.message.chat.id, call.message.message_id)
    
    try:
        doc = fitz.open(user_data[user_id])
        text = " ".join([page.get_text() for page in doc])
        doc.close()

        # طلب الأسئلة بالعربي
        prompt = f"Extract 3 medical MCQs in Arabic from this text: {text[:3000]}"
        response = model.generate_content(prompt)
        
        bot.send_message(call.message.chat.id, fix_arabic(response.text))
        
    except Exception as e:
        bot.send_message(call.message.chat.id, f"Error: {str(e)}")

bot.polling(none_stop=True)
