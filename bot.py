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

# إعداد ذكاء Gemini بطريقة متوافقة مع التحديثات الأخيرة
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    # تحديث الموديل ليتجنب خطأ 404
    model = genai.GenerativeModel(model_name="gemini-1.5-flash")

bot = telebot.TeleBot(API_TOKEN)
user_data = {}

def fix_arabic(text):
    if not text: return ""
    # تصحيح الحروف العربية وعكس الاتجاه لتظهر بشكل صحيح في التليجرام
    reshaped_text = arabic_reshaper.reshape(text)
    return get_display(reshaped_text)

def is_subscribed(user_id):
    try:
        status = bot.get_chat_member(CHANNEL_USERNAME, user_id).status
        return status in ['member', 'administrator', 'creator']
    except: return False

@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = f"أهلاً {message.from_user.first_name}! بوت التمريض والذكاء الاصطناعي جاهز لخدمتكم 💉."
    bot.reply_to(message, fix_arabic(welcome_text))

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
    markup.add(telebot.types.InlineKeyboardButton("📝 صنع اختبار ذكي (Gemini)", callback_data="make_quiz"))
    bot.reply_to(message, fix_arabic("تم استلام المحاضرة. اختر ما تريد فعله:"), reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "make_quiz")
def callback_quiz(call):
    user_id = call.from_user.id
    if user_id not in user_data: return
    
    bot.edit_message_text(fix_arabic("⏳ جاري تحليل المحاضرة وصنع الأسئلة..."), call.message.chat.id, call.message.message_id)
    
    try:
        doc = fitz.open(user_data[user_id])
        text = " ".join([page.get_text() for page in doc])
        doc.close()
        
        # طلب الأسئلة من Gemini
        prompt = f"Extract 3 multiple choice questions in Arabic from this medical text: {text[:3000]}"
        response = model.generate_content(prompt)
        
        # إرسال النتيجة مع تصحيح اللغة العربية
        bot.send_message(call.message.chat.id, fix_arabic(response.text))
        
    except Exception as e:
        bot.send_message(call.message.chat.id, f"Error: {str(e)}")

if __name__ == "__main__":
    bot.polling(none_stop=True)
    
