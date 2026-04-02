import telebot
import os
# لا نحتاج لـ load_dotenv هنا لأن Railway يتكفل بالأمر

# --- إعدادات الحماية والتوكن (من Railway) ---

# Railway سيقوم بتوفير هذا المتغير تلقائياً
# تأكد أنك اسميت المتغير في إعدادات Railway بـ "TELEGRAM_BOT_TOKEN"
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# التحقق من أن التوكن تم تحميله بنجاح من بيئة Railway
if BOT_TOKEN is None:
    print("❌ خطأ: لم يتم العثور على 'TELEGRAM_BOT_TOKEN' في متغيرات بيئة Railway.")
    # في بيئة الإنتاج، قد لا تريد عمل exit() مباشرة بل تسجيل الخطأ،
    # ولكن للتأكد من الإعدادات الآن سنتركها.
    exit()

bot = telebot.TeleBot(BOT_TOKEN)

# مجلد مؤقت لحفظ الملفات.Railway لديه نظام ملفات مؤقت ephemeral.
# هذا المجلد سيعمل طالما أن الـ Service تعمل، لكنه سيحذف عند إعادة التشغيل (Redeploy).
# هذا مناسب جداً لحالتنا حيث نريد معالجة الملف وإرساله ثم حذفه.
UPLOAD_FOLDER = 'downloads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# --- معالجة الرسائل ---

# 1. الاستجابة للأمر /start
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "أهلاً بك في بوت ترجمة ملفات PDF الطبية! 🦷\n\n"
        "أرسل لي ملف PDF، وسأقوم بترجمته إلى اللغة العربية والحفاظ على التنسيق قدر الإمكان.\n"
        "ملاحظة: هذا البوت مصمم للمشاريع الدراسية ومشغل على Railway."
    )
    bot.reply_to(message, welcome_text)

# 2. الاستجابة عند إرسال ملف (Document)
@bot.message_handler(content_types=['document'])
def handle_docs(message):
    chat_id = message.chat.id
    src_filename = None # تعريف المتغير خارج الـ try لاستخدامه في الـ finally

    try:
        file_info = bot.get_file(message.document.file_id)
        
        # التحقق من أن الملف هو PDF
        if not message.document.file_name.lower().endswith('.pdf'):
            bot.reply_to(message, "⚠️ عذراً، هذا البوت يدعم ملفات PDF فقط.")
            return

        bot.reply_to(message, "⏳ جاري استلام الملف ومعالجته على السيرفر... يرجى الانتظار.")

        # تحديد مسار حفظ الملف محلياً في مجلد downloads
        downloaded_file = bot.download_file(file_info.file_path)
        src_filename = os.path.join(UPLOAD_FOLDER, message.document.file_name)
        
        # حفظ الملف مؤقتاً على سيرفر Railway
        with open(src_filename, 'wb') as new_file:
            new_file.write(downloaded_file)

        # ---------------------------------------------------------
        # (المرحلة القادمة: هنا سنضع كود pymupdf، deep-translator، fpdf2)
        # ---------------------------------------------------------
        
        # مؤقتاً: سنخبر المستخدم بنجاح التحميل
        bot.send_message(chat_id, f"✅ تم تحميل الملف '{message.document.file_name}' بنجاح على Railway.\nجاري العمل على إضافة ميزة الترجمة في الخطوة القادمة.")

    except Exception as e:
        bot.reply_to(message, f"❌ حدث خطأ أثناء معالجة الملف: {e}")
    
    # ننصح دائماً بحذف الملفات المؤقتة بعد الانتهاء، لكن سنتركها الآن
    # حتى نتأكد من أن الكود يعمل، وفي المراحل القادمة سنضيف os.remove(src_filename)

# --- تشغيل البوت ---
print("البوت يعمل الآن على Railway... بانتظار الملفات.")
bot.infinity_polling()
