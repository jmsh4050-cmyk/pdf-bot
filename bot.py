import telebot
import fitz  # PyMuPDF
from deep_translator import GoogleTranslator
import os
import arabic_reshaper
from bidi.algorithm import get_display

# --- الإعدادات الأساسية ---
API_TOKEN = '8723000364:AAE8SsJWHUSrFllzTFvNRRsSRJBuhBtVC3E'
bot = telebot.TeleBot(API_TOKEN)

# دالة إصلاح اللغة العربية (RTL + Reshaping)
def fix_arabic(text):
    if not text: return ""
    reshaped_text = arabic_reshaper.reshape(text)
    return get_display(reshaped_text)

# دالة تحويل رقم اللون (Integer) إلى RGB
def get_rgb(color_int):
    if isinstance(color_int, int):
        r = ((color_int >> 16) & 0xFF) / 255
        g = ((color_int >> 8) & 0xFF) / 255
        b = (color_int & 0xFF) / 255
        return (r, g, b)
    return (0, 0, 0) # افتراضي أسود

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "🚀 بوت الترجمة الاحترافي جاهز!\nسأقوم بإعادة بناء ملزمتك بنفس التنسيق مع ترجمة تحت كل سطر (عربي RTL).")

@bot.message_handler(content_types=['document'])
def handle_pdf(message):
    if not message.document.file_name.lower().endswith('.pdf'):
        bot.reply_to(message, "يرجى إرسال ملف PDF فقط.")
        return

    file_info = bot.get_file(message.document.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    
    input_path = f"raw_{message.chat.id}.pdf"
    output_path = f"Pro_Translated_{message.document.file_name}"
    
    with open(input_path, 'wb') as f:
        f.write(downloaded_file)

    bot.reply_to(message, "⏳ جاري تحليل الملزمة وترجمتها بدقة... يرجى الانتظار.")

    try:
        doc = fitz.open(input_path)
        new_doc = fitz.open()
        font_path = "Amiri.ttf" # تأكد من وجود ملف الخط في السيرفر

        for page in doc:
            # إنشاء صفحة جديدة بنفس أبعاد الأصل
            new_page = new_doc.new_page(width=page.rect.width, height=page.rect.height)
            
            # 1. نقل الصور لمواقعها الأصلية
            for img_info in page.get_image_info():
                try:
                    new_page.insert_image(img_info["bbox"], stream=doc.extract_image(img_info["xref"])["image"])
                except: pass

            # 2. استخراج النصوص كـ "قاموس" (Dict) للحصول على كل التفاصيل
            blocks = page.get_text("dict")["blocks"]
            y_extra_shift = 0 # إزاحة تراكمية لترك مساحة للترجمة

            for b in blocks:
                if "lines" in b:
                    for l in b["lines"]:
                        for s in l["spans"]:
                            txt = s["text"].strip()
                            if len(txt) < 2: continue # تخطي الأحرف الوحيدة أو الفراغات
                            
                            origin_x, origin_y = s["origin"]
                            original_size = s["size"]
                            bbox = s["bbox"]

                            try:
                                # الترجمة
                                trans = GoogleTranslator(source='en', target='ar').translate(txt)
                                fixed_ar = fix_arabic(trans)

                                # حساب الموقع الجديد (الأصلي + الإزاحة)
                                current_y = origin_y + y_extra_shift

                                # كتابة النص الإنجليزي (اللون الأصلي أو أسود)
                                new_page.insert_text((origin_x, current_y), txt, 
                                                   fontsize=original_size, 
                                                   color=(0,0,0))

                                # إضافة إزاحة تحت النص الإنجليزي لكتابة العربي
                                y_extra_shift += original_size + 5
                                
                                # كتابة النص العربي (أحمر + محاذاة لليمين)
                                # نستخدم textbox لضبط الاتجاه RTL بدقة
                                rect_ar = fitz.Rect(bbox[0], current_y + 2, bbox[2], current_y + original_size + 15)
                                new_page.insert_textbox(rect_ar, fixed_ar, 
                                                       fontsize=original_size * 0.9, 
                                                       fontname="f0", fontfile=font_path,
                                                       color=(0.8, 0, 0), 
                                                       align=fitz.TEXT_ALIGN_RIGHT)
                                
                                # زيادة الإزاحة استعداداً للسطر القادم (فراغ سطر)
                                y_extra_shift += original_size + 10

                            except: continue

            # التحقق إذا كانت الإزاحة تجاوزت طول الصفحة (اختياري للنظم المتقدمة)
            # ملاحظة: في الملازم المزدحمة جداً قد تحتاج لتقليل y_extra_shift

        new_doc.save(output_path)
        new_doc.close()
        doc.close()

        with open(output_path, 'rb') as f:
            bot.send_document(message.chat.id, f, caption="✅ تم استكمال الملزمة بنظام التنسيق المتقدم.")
            
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ تقني: {str(e)}")
    
    # تنظيف السيرفر
    if os.path.exists(input_path): os.remove(input_path)
    if os.path.exists(output_path): os.remove(output_path)

bot.polling()
