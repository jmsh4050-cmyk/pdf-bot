import telebot
import fitz  # PyMuPDF
import os

# --- الإعدادات ---
API_TOKEN = '8723000364:AAE8SsJWHUSrFllzTFvNRRsSRJBuhBtVC3E'
bot = telebot.TeleBot(API_TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "مرحباً! سأقوم الآن بإعادة تنسيق الملزمة (نص إنجليزي متباعد) لتسهيل ترجمتها لاحقاً 📝✅")

@bot.message_handler(content_types=['document'])
def handle_pdf(message):
    if not message.document.file_name.lower().endswith('.pdf'):
        bot.reply_to(message, "يرجى إرسال ملف PDF.")
        return

    file_info = bot.get_file(message.document.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    
    input_path = f"prep_in_{message.chat.id}.pdf"
    output_path = f"Prepared_{message.document.file_name}"
    
    with open(input_path, 'wb') as f:
        f.write(downloaded_file)

    try:
        doc = fitz.open(input_path)
        new_doc = fitz.open()

        for page in doc:
            # إنشاء صفحة بيضاء جديدة
            new_page = new_doc.new_page(width=page.rect.width, height=page.rect.height)
            y_offset = 50  # البداية من الأعلى
            page_width = page.rect.width
            margin = 50    # هوامش جانبية مرتبة

            # 1. نقل الصور ووضعها بشكل ممركز لترك مساحة للنص
            for img_info in page.get_image_info():
                try:
                    img_rect = fitz.Rect(margin, y_offset, page_width - margin, y_offset + 180)
                    new_page.insert_image(img_rect, stream=doc.extract_image(img_info["xref"])["image"], keep_proportion=True)
                    y_offset += 200 # مسافة بعد الصورة
                    break 
                except: pass

            # 2. استخراج النصوص وإعادة توزيعها بفراغات كبيرة
            # نستخدم "blocks" للحصول على الفقرات كاملة
            blocks = page.get_text("blocks")
            for block in blocks:
                txt = block[4].replace('\n', ' ').strip() # تنظيف النص من الانكسارات العشوائية
                
                if len(txt) < 3: continue # تجاهل الرموز الصغيرة
                
                # تحديد الحجم (16 للعناوين، 14 للفقرات)
                is_title = len(txt) < 40 
                current_size = 16 if is_title else 14
                
                # فحص المساحة المتبقية في الصفحة
                if y_offset > page.rect.height - 100:
                    new_page = new_doc.new_page(width=page.rect.width, height=page.rect.height)
                    y_offset = 50

                # رسم النص الإنجليزي في صندوق يمتد بعرض الورقة
                # وضعنا الارتفاع 150 لكي يسمح للنص الطويل بالالتفاف تلقائياً
                rect_en = fitz.Rect(margin, y_offset, page_width - margin, y_offset + 150)
                
                # إدراج النص والحصول على الارتفاع الفعلي الذي استهلكه النص
                actual_height = new_page.insert_textbox(rect_en, txt, 
                                                       fontsize=current_size, 
                                                       color=(0, 0, 0), # أسود
                                                       align=fitz.TEXT_ALIGN_LEFT)
                
                # المسافة السحرية: نزيد الـ y_offset بمقدار النص + فراغ كبير جداً للترجمة
                # هنا نترك "فراغ" عمودي بمقدار 50 بكسل تحت كل فقرة
                y_offset += abs(actual_height) + 50 

        new_doc.save(output_path)
        new_doc.close()
        doc.close()
        
        with open(output_path, 'rb') as f:
            bot.send_document(message.chat.id, f, caption="✅ الملزمة جاهزة الآن! النصوص مرتبة ومتباعدة جداً للسماح بالترجمة مستقبلاً.")
            
    except Exception as e:
        bot.reply_to(message, f"خطأ أثناء التحضير: {str(e)}")
    
    if os.path.exists(input_path): os.remove(input_path)
    if os.path.exists(output_path): os.remove(output_path)

bot.polling()
