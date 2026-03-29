import telebot
import fitz  # PyMuPDF
from deep_translator import GoogleTranslator
import os
import arabic_reshaper
from bidi.algorithm import get_display

# --- الإعدادات ---
# استبدل التوكن الخاص بك هنا للتجربة
API_TOKEN = '7924093069:AAGjjy7SomYnfUWSWu1xGY337aIYzT42tCA'
CHANNEL_USERNAME = '@W_S_B52' 

bot = telebot.TeleBot(API_TOKEN)

def fix_arabic(text):
    """تصحيح عرض اللغة العربية"""
    reshaped_text = arabic_reshaper.reshape(text)
    return get_display(reshaped_text)

def contains_arabic(text):
    """فحص إذا كان النص يحتوي على حروف عربية"""
    return any("\u0600" <= char <= "\u06FF" for char in text)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, f"أهلاً وسام! أرسل ملف PDF لتجربة شكل الهايلايت الجديد.\nقناتنا: {CHANNEL_USERNAME}")

@bot.message_handler(content_types=['document'])
def handle_docs(message):
    user_id = message.from_user.id
    
    # التأكد من صيغة الملف
    if not message.document.file_name.lower().endswith('.pdf'):
        bot.reply_to(message, "يرجى إرسال ملف PDF فقط.")
        return

    msg = bot.reply_to(message, "⏳ جاري تطبيق شكل الهايلايت... انتظر قليلاً.")

    try:
        # تحميل الملف
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        input_pdf = f"in_{user_id}.pdf"
        # اسم الملف الجديد لتجربته
        output_pdf = f"Highlight_{message.document.file_name}"

        with open(input_pdf, 'wb') as f:
            f.write(downloaded_file)

        # فتح الملف الأصلي
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
                            
                            # نترجم فقط إذا النص مو عربي وطوله مناسب
                            if len(original_text) > 3 and not contains_arabic(original_text):
                                try:
                                    # إحداثيات النص الأصلي
                                    rect = span["bbox"] # [x0, y0, x1, y1]
                                    
                                    # 1. تصغير النص الإنكليزي قليلاً (0.90) لإفساح المجال
                                    eng_sz = span["size"] * 0.90
                                    
                                    # 2. حقن الإنكليزي الجديد (مكانه أو بإزاحة بسيطة للأعلى)
                                    page.insert_text(
                                        fitz.Point(rect[0], rect[1] + eng_sz), 
                                        original_text,
                                        fontsize=eng_sz,
                                        color=(0, 0, 0) # أسود للأصلي
                                    )
                                    
                                    # 3. ترجمة العربي
                                    translated = GoogleTranslator(source='en', target='ar').translate(original_text)
                                    fixed_ar = fix_arabic(translated)
                                    
                                    # 4. إضافة "الهايلايت" (مستطيل ملون خلف العربي)
                                    # نضع المستطيل تحت الإنكليزي مباشرة
                                    ar_sz = span["size"] * 0.70
                                    # [x0, y0, x1, y1] - نحدد المستطيل خلف النص العربي
                                    highlight_rect = [rect[0], rect[3], rect[2], rect[3] + ar_sz + 2]
                                    
                                    # رسم الهايلايت (لون سمائي فاتح)
                                    page.draw_rect(highlight_rect, color=(0.9, 0.95, 1), fill=(0.9, 0.95, 1))
                                    
                                    # 5. حقن العربي فوق الهايلايت
                                    page.insert_text(
                                        fitz.Point(rect[0], highlight_rect[3] - 1), 
                                        fixed_ar,
                                        fontsize=ar_sz,
                                        fontname="f0", 
                                        fontfile=font_path,
                                        color=(0.1, 0.4, 0.8) # أزرق هادئ
                                    )
                                except:
                                    continue

        # حفظ الملف المعدل
        doc.save(output_pdf)
        doc.close()

        # إرسال الملف المترجم
        with open(output_pdf, 'rb') as f:
            bot.send_document(message.chat.id, f, caption=f"✅ تم تطبيق شكل الهايلايت بنجاح لدفعة أبطال التمريض🔥\nالقناة: {CHANNEL_USERNAME}")

        # تنظيف الملفات المؤقتة
        if os.path.exists(input_pdf): os.remove(input_pdf)
        if os.path.exists(output_pdf): os.remove(output_pdf)

    except Exception as e:
        bot.reply_to(message, f"❌ حدث خطأ: {str(e)}\nتأكد من وجود ملف الخط Amiri.ttf")

# تشغيل البوت
bot.polling()
