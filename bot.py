import telebot
import os
import fitz  # PyMuPDF
from deep_translator import GoogleTranslator
from fpdf import FPDF
import arabic_reshaper
from bidi.algorithm import get_display

# --- إعدادات الحماية والتوكن (من Railway) ---
# ستقوم Railway بحقن هذا المتغير تلقائياً
# تأكد من إضافة Variable في Railway باسم: TELEGRAM_BOT_TOKEN
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if BOT_TOKEN is None:
    print("❌ خطأ: لم يتم العثور على 'TELEGRAM_BOT_TOKEN' في متغيرات بيئة Railway.")
    exit()

bot = telebot.TeleBot(BOT_TOKEN)

# مجلدات مؤقتة للملفات
DOWNLOADS_DIR = 'downloads'
OUTPUT_DIR = 'output'

for folder in [DOWNLOADS_DIR, OUTPUT_DIR]:
    if not os.path.exists(folder):
        os.makedirs(folder)

# اسم ملف الخط العربي (يجب أن يكون مرفوعاً مع المشروع)
FONT_FILE = 'Arial.ttf' 

# --- وظائف معالجة النصوص العربية والـ PDF ---

def process_arabic_text(text):
    """إعادة تشكيل النص العربي وتصحيح الاتجاه (RTL)"""
    if not text.strip():
        return ""
    # إعادة تشكيل الحروف
    reshaped_text = arabic_reshaper.reshape(text)
    # تصحيح الاتجاه ليكون من اليمين لليسار
    bidi_text = get_display(reshaped_text)
    return bidi_text

def translate_pdf(input_path, output_path):
    """قراءة، ترجمة، وإنشاء PDF جديد"""
    
    # 1. فتح ملف الـ PDF الأصلي وقراءة النصوص
    try:
        doc = fitz.open(input_path)
    except Exception as e:
        raise Exception(f"خطأ في فتح ملف PDF: {e}")

    # 2. إعداد ملف الـ PDF الجديد (fpdf2)
    pdf = FPDF()
    
    # التأكد من وجود ملف الخط
    if not os.path.exists(FONT_FILE):
        # هذه خطوة حرجة، إذا لم يوجد الخط لن تظهر العربية
        raise FileNotFoundError(f"⚠️ ملف الخط '{FONT_FILE}' غير موجود! لن تظهر اللغة العربية بدونه.")

    # إضافة الخط العربي وتعريفه كخط يدعم الـ Unicode
    pdf.add_font('ArabicFont', '', FONT_FILE, uni=True)
    pdf.set_font('ArabicFont', size=12)
    
    # إعدادات الصفحة (الهوامش والاتجاه)
    pdf.set_margins(10, 10, 10)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_rtl(True) # تفعيل الكتابة من اليمين لليسار عالمياً في الملف

    total_pages = len(doc)
    
    # مترجم محرك جوجل
    translator = GoogleTranslator(source='auto', target='ar')

    # 3. معالجة كل صفحة
    for page_num in range(total_pages):
        page = doc[page_num]
        
        # استخراج النص من الصفحة الحالية (ككتل نصوص للحفاظ على بعض الهيكل)
        text_blocks = page.get_text("blocks")
        
        pdf.add_page() # إضافة صفحة جديدة في الملف الناتج لكل صفحة أصلية
        
        # كتابة رقم الصفحة (اختياري)
        pdf.set_font('ArabicFont', size=10)
        pdf.cell(0, 10, process_arabic_text(f"صفحة {page_num + 1}"), ln=1, align='C')
        pdf.set_font('ArabicFont', size=12)

        for block in text_blocks:
            text = block[4] # النص موجود في العنصر الخامس من الكتلة
            
            # تنظيف النص وترجمته إذا لم يكن فارغاً
            clean_text = text.strip()
            if clean_text:
                try:
                    # تقسيم النص الطويل لتجنب مشاكل الـ API الخاصة بالترجمة (إذا لزم الأمر)
                    if len(clean_text) > 4000:
                        # هذا تقسيم بسيط جداً، يمكن تحسينه
                        translated_text = ""
                        parts = [clean_text[i:i+4000] for i in range(0, len(clean_text), 4000)]
                        for part in parts:
                            translated_text += translator.translate(part)
                    else:
                        translated_text = translator.translate(clean_text)
                    
                    # معالجة النص المترجم للعرض الصحيح باللغة العربية
                    final_text = process_arabic_text(translated_text)
                    
                    # كتابة النص في ملف PDF الناتج
                    # multi_cell تتعامل مع السطور المتعددة تلقائياً
                    pdf.multi_cell(0, 8, final_text, align='R')
                    
                except Exception as t_err:
                    print(f"Error during translation/writing block: {t_err}")
                    # في حال فشل ترجمة كتلة معينة، نكتب النص الأصلي (مع تفعيل RTL)
                    pdf.multi_cell(0, 8, process_arabic_text(f"[خطأ في الترجمة]: {clean_text}"), align='R')

    # 4. حفظ ملف الـ PDF الناتج
    try:
        pdf.output(output_path)
        doc.close()
    except Exception as e:
        raise Exception(f"خطأ في حفظ ملف PDF الناتج: {e}")

# --- معالجة رسائل تيليجرام ---

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "أهلاً بك في بوت ترجمة ملفات PDF الطبية! 🦷🇹🇳\n\n"
        "أرسل لي ملف PDF، وسأقوم بترجمته إلى اللغة العربية (محرك جوجل).\n\n"
        "⚠️ هام جداً لمشروعك الدراسية:\n"
        "1. الترجمة آلية وقد تحتاج لمراجعة بشرية.\n"
        "2. البوت يحافظ على النص ولكنه **لا يحافظ على التنسيق المعقد** (الصور، الجداول بدقة، الأماكن الدقيقة للنصوص).\n"
        "3. يرجى الانتظار، فالمعالجة قد تستغرق وقتاً حسب حجم الملف."
    )
    bot.reply_to(message, welcome_text)

@bot.message_handler(content_types=['document'])
def handle_docs(message):
    chat_id = message.chat.id
    src_filename = None
    output_filename = None

    # التحقق من أن الملف هو PDF
    if not message.document.file_name.lower().endswith('.pdf'):
        bot.reply_to(message, "⚠️ عذراً، هذا البوت يدعم ملفات PDF فقط.")
        return

    # إرسال رسالة حالة للمستخدم
    status_message = bot.reply_to(message, "⏳ جاري استلام الملف... يرجى الانتظار.")

    try:
        file_info = bot.get_file(message.document.file_id)
        
        # تحديد المسارات
        safe_filename = "".join([c for c in message.document.file_name if c.isalpha() or c.isdigit() or c==' ' or c=='.']).rstrip()
        src_filename = os.path.join(DOWNLOADS_DIR, f"{chat_id}_{safe_filename}")
        output_filename = os.path.join(OUTPUT_DIR, f"translated_{chat_id}_{safe_filename}")

        # 1. تحميل الملف مؤقتاً
        downloaded_file = bot.download_file(file_info.file_path)
        with open(src_filename, 'wb') as new_file:
            new_file.write(downloaded_file)

        # 2. تحديث الحالة وبدء الترجمة
        bot.edit_message_text("⏳ جاري قراءة الملف وترجمته وإنشاء ملف جديد... هذا قد يستغرق بعض الوقت.", chat_id, status_message.message_id)
        
        # تشغيل دالة الترجمة
        translate_pdf(src_filename, output_filename)

        # 3. إرسال الملف المترجم
        bot.edit_message_text("✅ تمت الترجمة بنجاح! جاري إرسال الملف...", chat_id, status_message.message_id)
        with open(output_filename, 'rb') as f:
            bot.send_document(chat_id, f, caption="إليك الملف المترجم.")

    except FileNotFoundError as fnf:
        bot.edit_message_text(f"❌ خطأ فني: {fnf}", chat_id, status_message.message_id)
    except Exception as e:
        print(f"Critical Error: {e}")
        bot.edit_message_text(f"❌ حدث خطأ غير متوقع أثناء معالجة الملف: {str(e)}", chat_id, status_message.message_id)
    
    finally:
        # تنظيف الملفات المؤقتة للحفاظ على مساحة سيرفر Railway
        if src_filename and os.path.exists(src_filename):
            os.remove(src_filename)
        if output_filename and os.path.exists(output_filename):
            os.remove(output_filename)

# --- تشغيل البوت ---
print("البوت يعمل الآن على Railway... بانتظار الملفات.")
bot.infinity_polling()
        
