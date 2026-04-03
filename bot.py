import telebot
import fitz  # PyMuPDF
import os

# --- الإعدادات ---
API_TOKEN = '8723000364:AAE8SsJWHUSrFllzTFvNRRsSRJBuhBtVC3E'
bot = telebot.TeleBot(API_TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "تم ضبط البوت: نفس تنسيق الأصل وحجم الخط، مع إضافة سطر فارغ تحت كل جملة ✅")

@bot.message_handler(content_types=['document'])
def handle_pdf(message):
    if not message.document.file_name.lower().endswith('.pdf'):
        bot.reply_to(message, "يرجى إرسال ملف PDF.")
        return

    file_info = bot.get_file(message.document.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    
    input_path = f"orig_in_{message.chat.id}.pdf"
    output_path = f"Spaced_Original_{message.document.file_name}"
    
    with open(input_path, 'wb') as f:
        f.write(downloaded_file)

    try:
        doc = fitz.open(input_path)
        new_doc = fitz.open()

        for page in doc:
            # إنشاء صفحة جديدة بنفس أبعاد الأصل تماماً
            new_page = new_doc.new_page(width=page.rect.width, height=page.rect.height)
            
            # 1. نقل الصور لمواقعها الأصلية بدقة
            for img_info in page.get_image_info():
                try:
                    new_page.insert_image(img_info["bbox"], stream=doc.extract_image(img_info["xref"])["image"])
                except: pass

            # 2. معالجة النصوص (نفس الموقع + إزاحة)
            # نستخدم dict للحصول على الحجم والموقع واللون الأصلي
            blocks = page.get_text("dict")["blocks"]
            
            y_extra_shift = 0 # هذا العداد سيزيد الفراغ التراكمي
            
            for b in blocks:
                if "lines" in b:
                    for l in b["lines"]:
                        for s in l["spans"]:
                            txt = s["text"].strip()
                            if not txt: continue
                            
                            # أخذ الخصائص الأصلية
                            origin_x, origin_y = s["origin"]
                            original_size = s["size"]
                            original_color = s["color"]
                            
                            # تحويل اللون من عدد صحيح إلى RGB (0-1)
                            # PyMuPDF أحياناً يعطي اللون كقيمة واحدة
                            color_rgb = fitz.utils.getColor(original_color) if isinstance(original_color, int) else (0,0,0)

                            # الموقع الجديد = الموقع الأصلي + الفراغات المتراكمة
                            # سنضيف "سطر" (بمقدار حجم الخط + 10 بكسل) كفراغ للترجمة
                            new_y = origin_y + y_extra_shift
                            
                            # كتابة النص بنفس حجمه ولونه وموقعه
                            new_page.insert_text((origin_x, new_y), 
                                               txt, 
                                               fontsize=original_size, 
                                               color=color_rgb)
                            
                            # بعد كل سطر نكتبه، نزيد الإزاحة (كأننا تركنا سطر فارغ)
                            # الفراغ = حجم الخط الأصلي (لترك مساحة تكفي لترجمة بنفس الحجم)
                            y_extra_shift += original_size + 5 
                            
            # إذا الإزاحة خلت الكلام يطلع بره الورقة، يفضل تقليل الفراغ أو عمل صفحات إضافية
            # لكن حسب طلبك "نفس الأصل"، هذا التعديل يضيف الفراغ المطلوب تحت كل جملة.

        new_doc.save(output_path)
        new_doc.close()
        doc.close()
        
        with open(output_path, 'rb') as f:
            bot.send_document(message.chat.id, f, caption="✅ تم إضافة الفراغات مع الحفاظ على التنسيق الأصلي.")
            
    except Exception as e:
        bot.reply_to(message, f"خطأ: {str(e)}")
    
    if os.path.exists(input_path): os.remove(input_path)
    if os.path.exists(output_path): os.remove(output_path)

bot.polling()
