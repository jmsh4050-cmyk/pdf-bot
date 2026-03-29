import telebot
import fitz  # PyMuPDF
from deep_translator import GoogleTranslator
import os
import arabic_reshaper
from bidi.algorithm import get_display

# --- الإعدادات ---
API_TOKEN = '7924093069:AAGjjy7SomYnfUWSWu1xGY337aIYzT42tCA'
CHANNEL_USERNAME = '@W_S_B52' 

bot = telebot.TeleBot(API_TOKEN)

def fix_arabic(text):
    """تصحيح عرض اللغة العربية (قلب الحروف وتشكيلها)"""
    reshaped_text = arabic_reshaper.reshape(text)
    return get_display(reshaped_text)

def is_subscribed(user_id):
    """التحقق من الاشتراك في القناة"""
    try:
        status = bot.get_chat_member(CHANNEL_USERNAME, user_id).status
        return status in ['member', 'administrator', 'creator']
    except:
        return False

def contains_arabic(text):
    """فحص إذا كان النص يحتوي على حروف عربية لعدم ترجمتها"""
    return any("\u0600" <= char <= "\u06FF" for char in text)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, f"أهلاً وسام! أرسل ملف PDF لترجمته ترجمة احترافية فوق الأسطر الأصلية.\nقناتنا: {CHANNEL_USERNAME}")

@bot.message_handler(content_types=['document'])
def handle_docs(message):
    user_id = message.from_user.id
    
    # التحقق من الاشتراك
    if not is_subscribed(user_id):
        markup = telebot.types.InlineKeyboardMarkup()
        btn = telebot.types.InlineKeyboardButton("اشترك في القناة أولاً ✅", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")
        markup.add(btn)
        bot.reply_to(message, f"🚫 عذراً، اشترك في القناة لاستخدام البوت:\n{CHANNEL_USERNAME}", reply_markup=markup)
        return

    # التأكد من صيغة الملف
    if not message.document.file_name.lower().endswith('.pdf'):
        bot.reply_to(message, "يرجى إرسال ملف PDF فقط.")
        return

    msg = bot.reply_to(message, "⏳ جاري تحليل الملزمة وحقن الترجمة فوق النصوص... انتظر قليلاً.")

    try:
        # تحميل الملف
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        input_pdf = f"in_{user_id}.pdf"
        output_pdf = f"Translated_{message.document.file_name}"

        with open(input_pdf, 'wb') as f:
            f.write(downloaded_file)

        # فتح الملف الأصلي باستخدام PyMuPDF
        doc = fitz.open(input_pdf)
        font_path = "Amiri.ttf" # تأكد من وجود هذا الملف بجانب الكود

        for page in doc:
            # استخراج النصوص مع إحداثياتها الدقيقة
            dict_text = page.get_text("dict")
            for block in dict_text["blocks"]:
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            original_text = span["text"].strip()
                            
                            # شروط الترجمة: (طول النص > 3) و (لا يحتوي على عربي)
                            if len(original_text) > 3 and not contains_arabic(original_text):
                                try:
                                    # الترجمة من الإنكليزية للعربية
                                    translated = GoogleTranslator(source='en', target='ar').translate(original_text)
                                    fixed_ar = fix_arabic(translated)
                                    
                                    # إحداثيات النص (الـ bbox)
                                    rect = span["bbox"] # [x0, y0, x1, y1]
                                    
                                    # حقن الترجمة تحت السطر الأصلي مباشرة
                                    # حجم الخط 70% من الأصلي لتجنب التداخل
                                    page.insert_text(
                                        fitz.Point(rect[0], rect[3] + 1.5), 
                                        fixed_ar,
                                        fontsize=span["size"] * 0.7, 
                                        fontname="f0", 
                                        fontfile=font_path,
                                        color=(0, 0.4, 0.8) # لون أزرق دراسي مريح
                                    )
                                except:
                                    continue

        # حفظ الملف المعدل بنفس جودة الأصلي
        doc.save(output_pdf)
        doc.close()

        # إرسال الملف المترجم
        with open(output_pdf, 'rb') as f:
            bot.send_document(
                message.chat.id, 
                f, 
                caption=f"💙🔥تم الحقن المباشر للترجمة بنجاح لدفعة أبطالنه 🔥\nقناتنا: {CHANNEL_USERNAME}"
            )

        # تنظيف الملفات المؤقتة
        os.remove(input_pdf)
        os.remove(output_pdf)

    except Exception as e:
        bot.reply_to(message, f"❌ حدث خطأ: {str(e)}\nتأكد من وجود ملف الخط Amiri.ttf")

# تشغيل البوت
bot.polling()
