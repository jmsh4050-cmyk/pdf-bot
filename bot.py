import telebot
import fitz  # PyMuPDF
from deep_translator import GoogleTranslator
import os
import arabic_reshaper
from bidi.algorithm import get_display

# --- الإعدادات الأساسية (تم وضع التوكن مباشرة) ---
# التوكن الخاص ببوتك
BOT_TOKEN = '7924093069:AAGjjy7SomYnfUWSWu1xGY337aIYzT42tCA'

bot = telebot.TeleBot(BOT_TOKEN)

# مجلد مؤقت للملفات
DOWNLOADS_DIR = 'downloads'
if not os.path.exists(DOWNLOADS_DIR):
    os.makedirs(DOWNLOADS_DIR)

# --- التعديل هنا: استخدام خط Amiri.ttf ---
# تأكد من أن هذا الملف موجود في نفس مجلد ملف البوت على GitHub
FONT_FILE = 'Amiri.ttf' 

# --- وظائف معالجة النصوص العربية ---

def process_arabic_text(text):
    """إعادة تشكيل النص العربي وتصحيح الاتجاه (RTL)"""
    if not text or not text.strip():
        return ""
    try:
        # إعادة تشكيل الحروف لتبدو متصلة بشكل صحيح
        reshaped_text = arabic_reshaper.reshape(text)
        # تصحيح الاتجاه ليكون من اليمين لليسار
        bidi_text = get_display(reshaped_text)
        return bidi_text
    except Exception as e:
        print(f"Error processing Arabic text: {e}")
        return text # في حال الخطأ نعيد النص كما هو

def contains_arabic(text):
    """التحقق من احتواء النص على حروف عربية"""
    if not text: return False
    # التحقق من نطاق الحروف العربية في Unicode
    return any("\u0600" <= char <= "\u06FF" for char in text)

# --- معالجة رسائل تيليجرام ---

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    user_name = message.from_user.first_name 
    welcome_text = (
        f"أهلاً {user_name}! البوت جاهز لترجمة ملفات الـ PDF الطبية ✅\n\n"
        "أرسل ملف الـ PDF مباشرة، وسأقوم بترجمته إلى العربية باستخدام محرك جوجل.\n"
        "(الترجمة ستظهر تحت السطور الأصلية باللون الأحمر)."
    )
    bot.reply_to(message, welcome_text)

@bot.message_handler(content_types=['document'])
def handle_docs(message):
    chat_id = message.chat.id
    
    # التحقق من أن الملف هو PDF
    if not message.document.file_name.lower().endswith('.pdf'):
        bot.reply_to(message, "⚠️ عذراً، هذا البوت يدعم ملفات PDF فقط.")
        return

    # إرسال رسالة حالة للمستخدم
    status_message = bot.reply_to(message, "⏳ جاري استلام الملف ومعالجته... يرجى الانتظار.")
    
    src_filename = None
    output_filename = None

    try:
        # الحصول على معلومات الملف لتحميله
        file_info = bot.get_file(message.document.file_id)
        
        # تحديد مسارات الحفظ المؤقت (استخدام مجلد downloads للترتيب)
        # تنظيف اسم الملف من الحروف الخاصة
        safe_filename = "".join([c for c in message.document.file_name if c.isalpha() or c.isdigit() or c==' ' or c=='.']).rstrip()
        src_filename = os.path.join(DOWNLOADS_DIR, f"in_{chat_id}_{safe_filename}")
        output_filename = os.path.join(DOWNLOADS_DIR, f"translated_{chat_id}_{safe_filename}")

        # 1. تحميل الملف مؤقتاً
        downloaded_file = bot.download_file(file_info.file_path)
        with open(src_filename, 'wb') as new_file:
            new_file.write(downloaded_file)

        # 2. تحديث الحالة وبدء الترجمة
        bot.edit_message_text("⏳ جاري قراءة الملف وترجمته وإنشاء ملف جديد... هذا قد يستغرق بعض الوقت.", chat_id, status_message.message_id)
        
        # تشغيل دالة الترجمة (الترجمة تحت الخط بالأحمر)
        translate_with_red_arabic(src_filename, output_filename)

        # 3. إرسال الملف المترجم
        # نستخدم REPLY لكي يعرف المستخدم أي ملف تم ترجمته
        bot.edit_message_text("✅ تمت الترجمة بنجاح! جاري إرسال الملف...", chat_id, status_message.message_id)
        with open(output_filename, 'rb') as f:
            bot.send_document(chat_id, f, caption="✅ تم الإنجاز! الترجمة تحت السطور.")

    except Exception as e:
        print(f"Critical Error: {e}")
        # إبلاغ المستخدم بالخطأ بشكل مهذب، مع تفاصيل الخطأ (لأغراض التطوير حالياً)
        bot.edit_message_text(f"❌ حدث خطأ غير متوقع أثناء معالجة الملف: {str(e)}", chat_id, status_message.message_id)
    
    finally:
        # تنظيف الملفات المؤقتة للحفاظ على مساحة سيرفر Railway
        if src_filename and os.path.exists(src_filename):
            os.remove(src_filename)
        if output_filename and os.path.exists(output_filename):
            os.remove(output_filename)

# --- دالة الترجمة باستخدام PyMuPDF ---

def translate_with_red_arabic(input_path, output_path):
    """
    قراءة ملف PDF، الحفاظ على التنسيق الإنجليزي،
    وإضافة ترجمة عربية (أحمر) تحت كل سطر.
    """
    try:
        # فتح ملف الـ PDF الأصلي
        doc = fitz.open(input_path)
    except Exception as e:
        raise Exception(f"خطأ في فتح ملف PDF الأصلي: {e}")

    # التحقق من وجود ملف الخط (خطوة حرجة جداً للعربية)
    if not os.path.exists(FONT_FILE):
        raise FileNotFoundError(f"⚠️ ملف الخط '{FONT_FILE}' غير موجود! تأكد من رفعه بجانب الملف الرئيسي.")

    # مترجم محرك جوجل
    translator = GoogleTranslator(source='auto', target='ar')

    # معالجة كل صفحة
    for page in doc:
        try:
            # استخراج النص من الصفحة على شكل قاموس (dict) للحصول على معلومات الموقع (bbox)
            dict_text = page.get_text("dict")
            
            for block in dict_text["blocks"]:
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            txt = span["text"].strip()
                            
                            # معالجة النص فقط إذا لم يكن فارغاً ولا يحتوي على عربي (تجنب إعادة ترجمة المترجم)
                            if len(txt) > 2 and not contains_arabic(txt):
                                try:
                                    # الحصول على موقع النص الحالي (bbox: x0, y0, x1, y1)
                                    rect = span["bbox"]
                                    
                                    # 1. ترجمة النص إلى العربية
                                    translated_text = translator.translate(txt)
                                    
                                    # 2. معالجة النص العربي للعرض (تعديل الاتجاه والتشكيل)
                                    fixed_arabic = process_arabic_text(translated_text)
                                    
                                    if fixed_arabic:
                                        # 3. حساب موقع الترجمة العربية
                                        # سنستخدم حجم الخط الأصلي كقاعدة للإزاحة العمودية
                                        font_size = span["size"]
                                        offset_y = font_size * 1.3 # إزاحة لأسفل (تم زيادتها قليلاً لخط Amiri)

                                        # تحديد النقطة التي سنبدأ عندها الكتابة العربية
                                        # x0 (البداية الأفقية)، y1 (نهاية النص الأصلي من الأسفل) + الإزاحة
                                        arabic_start_point = fitz.Point(rect[0], rect[1] + offset_y)
                                        
                                        # 4. كتابة النص العربي المترجم في ملف الـ PDF الأصلي
                                        # color=(0.8, 0, 0) هو تدرج من اللون الأحمر
                                        # fontname="f0" و fontfile=FONT_FILE هما الطريقة لتعريف خط Unicode في fitz
                                        page.insert_text(arabic_start_point, 
                                                          fixed_arabic, 
                                                          fontsize=font_size * 0.9, # حجم الخط العربي أصغر قليلاً
                                                          fontname="f0", 
                                                          fontfile=FONT_FILE, 
                                                          color=(0.8, 0, 0)) # اللون الأحمر
                                except Exception as t_err:
                                    # تسجيل خطأ ترجمة كتلة محددة والاستمرار
                                    print(f"Error during translation/writing span: {t_err}")
                                    continue
        except Exception as p_err:
            # تسجيل خطأ معالجة صفحة والاستمرار
            print(f"Error processing page: {p_err}")
            continue

    # حفظ ملف الـ PDF الناتج
    try:
        # استخدام deflate=True لتقليل حجم الملف (غير ضروري ولكنه مفضل)
        doc.save(output_path, deflate=True)
        doc.close()
    except Exception as e:
        raise Exception(f"خطأ في حفظ ملف PDF الناتج: {e}")

# --- تشغيل البوت ---
print("البوت يعمل الآن... بانتظار الملفات.")
# استخدام infinity_polling لضمان استمرار عمل البوت وعدم توقفه عند الأخطاء البسيطة
bot.infinity_polling()
