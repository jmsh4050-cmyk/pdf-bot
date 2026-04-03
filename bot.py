import telebot
import fitz  # PyMuPDF
import os

# --- الإعدادات ---
API_TOKEN = '8723000364:AAE8SsJWHUSrFllzTFvNRRsSRJBuhBtVC3E'
bot = telebot.TeleBot(API_TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "أهلاً بك! تم إصلاح خطأ الألوان وتفعيل نظام الفراغات (سطر تحت كل جملة) ✅")

@bot.message_handler(content_types=['document'])
def handle_pdf(message):
    if not message.document.file_name.lower().endswith('.pdf'):
        bot.reply_to(message, "يرجى إرسال ملف PDF.")
        return

    file_info = bot.get_file(message.document.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    
    input_path = f"in_{message.chat.id}.pdf"
    output_path = f"Spaced_Fixed_{message.document.file_name}"
    
    with open(input_path, 'wb') as f:
        f.write(downloaded_file)

    try:
        doc = fitz.open(input_path)
        new_doc = fitz.open()

        for page in doc:
            # إنشاء صفحة جديدة بنفس أبعاد الأصل
            new_page = new_doc.new_page(width=page.rect.width, height=page.rect.height)
            
            # 1. نقل الصور لمواقعها الأصلية
            for img_info in page.get_image_info():
                try:
                    new_page.insert_image(img_info["bbox"], stream=doc.extract_image(img_info["xref"])["image"])
                except: pass

            # 2. معالجة النصوص (نفس الموقع + إزاحة سطر فارغ)
            blocks = page.get_text("dict")["blocks"]
            y_extra_shift = 0 # عداد الفراغ التراكمي
            
            for b in blocks:
                if "lines" in b:
                    for l in b["lines"]:
                        for s in l["spans"]:
                            txt = s["text"].strip()
                            if not txt: continue
                            
                            origin_x, origin_y = s["origin"]
                            original_size = s["size"]
                            original_color = s["color"]

                            # --- إصلاح خطأ اللون ---
                            # نحول رقم اللون إلى تنسيق RGB (Red, Green, Blue) يتقبله التابع insert_text
                            if isinstance(original_color, int):
                                # تحويل الرقم الصحيح إلى ثلاثية (R, G, B)
                                r = ((original_color >> 16) & 0xFF) / 255
                                g = ((original_color >> 8) & 0xFF) / 255
                                b_color = (original_color & 0xFF) / 255
                                final_color = (r, g, b_color)
                            else:
                                final_color = (0, 0, 0) # افتراضي أسود إذا فشل التحويل

                            # حساب الموقع الجديد مع الفراغ
                            new_y = origin_y + y_extra_shift
                            
                            # إذا النص خرج عن الصفحة، نفتح صفحة جديدة (اختياري لكن مفيد)
                            if new_y > page.rect.height - 20:
                                new_page = new_doc.new_page(width=page.rect.width, height=page.rect.height)
                                y_extra_shift = -origin_y + 50 # تصفير الإزاحة للصفحة الجديدة
                                new_y = 50

                            # كتابة النص بنفس التنسيق الأصلي
                            new_page.insert_text((origin_x, new_y), 
                                               txt, 
                                               fontsize=original_size, 
                                               color=final_color)
                            
                            # إضافة "فراغ بمقدار سطر" تحت كل نص
                            # نزيد الإزاحة بمقدار حجم الخط + مسافة بسيطة
                            y_extra_shift += original_size + 10 
                            
        new_doc.save(output_path)
        new_doc.close()
        doc.close()
        
        with open(output_path, 'rb') as f:
            bot.send_document(message.chat.id, f, caption="✅ تم التنسيق بنجاح مع إضافة سطر فارغ تحت كل نص.")
            
    except Exception as e:
        bot.reply_to(message, f"حدث خطأ أثناء المعالجة: {str(e)}")
    
    if os.path.exists(input_path): os.remove(input_path)
    if os.path.exists(output_path): os.remove(output_path)

bot.polling()
