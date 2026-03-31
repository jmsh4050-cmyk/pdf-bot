import os
import telebot
import fitz  # PyMuPDF
from deep_translator import GoogleTranslator
import arabic_reshaper
from bidi.algorithm import get_display
import google.generativeai as genai

# --- الإعدادات (تأكد من كتابة GEMINI_KEY في Railway) ---
API_TOKEN = '7924093069:AAGjjy7SomYnfUWSWu1xGY337aiYzT42tCA'
CHANNEL_USERNAME = '@W_S_B52'
BOT_LINK = 'https://t.me/WSM_bot'

# إعداد ذكاء Gemini المحمي (يسحب المفتاح سراً من Railway)
GEMINI_API_KEY = os.getenv("GEMINI_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    print("⚠️ المفتاح السري مفقود من إعدادات Railway!")

bot = telebot.TeleBot(API_TOKEN)
user_data = {}

def fix_arabic(text):
    if not text: return ""
    reshaped_text = arabic_reshaper.reshape(text)
    return get_display(reshaped_text)

def is_subscribed(user_id):
    try:
        status = bot.get_chat_member(CHANNEL_USERNAME, user_id).status
        return status in ['member', 'administrator', 'creator']
    except: return False

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_name = message.from_user.first_name
    bot.reply_to(message, f"أهلاً {user_name}! تم تفعيل ذكاء Gemini لخدمتكم 💉✨")

@bot.message_handler(content_types=['document'])
def handle_docs(message):
    user_id = message.from_user.id
    if not is_subscribed(user_id):
        markup = telebot.types.InlineKeyboardMarkup()
        btn = telebot.types.InlineKeyboardButton("✅ اشترك في القناة أولاً", url=f'https://t.me/{CHANNEL_USERNAME[1:]}')
        markup.add(btn)
        bot.reply_to(message, f"عذراً، اشترك في القناة لاستخدام البوت: {CHANNEL_USERNAME}", reply_markup=markup)
        return

    # حفظ الملف مؤقتاً
    file_info = bot.get_file(message.document.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    file_path = f"temp_{user_id}.pdf"
    
    with open(file_path, 'wb') as f:
        f.write(downloaded_file)
    
    user_data[user_id] = file_path
    
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("📝 صنع اختبار ذكي (Gemini)", callback_data="make_quiz"))
    bot.reply_to(message, "تم استلام المحاضرة، اختر ما تريد فعله:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "make_quiz")
def callback_quiz(call):
    user_id = call.from_user.id
    if user_id not in user_data:
        bot.answer_callback_query(call.id, "أعد إرسال الملف مرة أخرى.")
        return

    bot.edit_message_text("⏳ جاري تحليل المحاضرة وصنع الأسئلة...", call.message.chat.id, call.message.message_id)
    
    try:
        # استخراج النص من الـ PDF
        doc = fitz.open(user_data[user_id])
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()

        # طلب توليد الأسئلة من Gemini
        prompt = f"Extract 3 multiple choice questions in Arabic from this medical text: {text[:3000]}"
        response = model.generate_content(prompt)
        
        # إرسال النتيجة (هنا البوت يرسل النص الذي ولده جمناي)
        bot.send_message(call.message.chat.id, fix_arabic(response.text))
        
    except Exception as e:
        bot.send_message(call.message.chat.id, f"❌ حدث خطأ: {str(e)}")

bot.polling(none_stop=True)
