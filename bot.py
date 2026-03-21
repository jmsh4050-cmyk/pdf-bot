import telebot
from fpdf import FPDF

# --- الإعدادات الأساسية ---
API_TOKEN = '7924093069:AAGjjy7SomYnfUWSWu1xGY337aIYzT42tCA'
CHANNEL_ID = '@W_S_B52'  # معرف قناتك
bot = telebot.TeleBot(API_TOKEN)

# دالة التحقق من الاشتراك الإجباري
def is_subscribed(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_ID, user_id)
        if member.status in ['member', 'administrator', 'creator']:
            return True
        return False
    except:
        return False

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    if not is_subscribed(user_id):
        bot.reply_to(message, f"❌ عذراً! يجب عليك الاشتراك في قناة البوت أولاً لاستخدامه:\n\n{CHANNEL_ID}\n\nبعد الاشتراك، أرسل /start مجدداً.")
        return
    
    bot.reply_to(message, "✅ أهلاً بك! أنا بوت تحويل النصوص إلى PDF. أرسل لي أي نص الآن وسأقوم بتحويله لك.")

@bot.message_handler(func=lambda message: True)
def create_pdf(message):
    user_id = message.from_user.id
    
    # تحقق من الاشتراك قبل المعالجة
    if not is_subscribed(user_id):
        bot.reply_to(message, f"⚠️ توقف! يجب أن تشترك بالقناة أولاً:\n{CHANNEL_ID}")
        return

    try:
        pdf = FPDF()
        pdf.add_page()
        # تأكد أن اسم ملف الخط في GitHub هو Amiri-Regular.ttf
        pdf.add_font('Amiri', '', 'Amiri-Regular.ttf', uni=True)
        pdf.set_font('Amiri', size=15)
        
        # كتابة النص بمحاذاة اليمين ليدعم العربية
        pdf.multi_cell(0, 10, txt=message.text, align='R')
        
        pdf_file = "output.pdf"
        pdf.output(pdf_file)
        
        with open(pdf_file, 'rb') as f:
            bot.send_document(message.chat.id, f, caption="تم تحويل النص إلى PDF بنجاح 📄")
    except Exception as e:
        bot.reply_to(message, "حدث خطأ فني، تأكد من وجود ملف الخط Amiri-Regular.ttf في المستودع.")

bot.polling()

