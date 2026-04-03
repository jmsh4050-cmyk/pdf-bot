import telebot
import fitz  # PyMuPDF
from deep_translator import GoogleTranslator
import os
import arabic_reshaper
from bidi.algorithm import get_display

# --- الإعدادات ---
API_TOKEN = '8723000364:AAE8SsJWHUSrFllzTFvNRRsSRJBuhBtVC3EA'
bot = telebot.TeleBot(API_TOKEN)

def fix_arabic(text):
    if not text: return ""
    reshaped_text = arabic_reshaper.reshape(text)
    return get_display(reshaped_text)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "أهلاً بك! أرسل ملف الـ PDF وسأقوم بإعادة صياغته كملزمة مترجمة بدون تداخل ✅")

@bot.message_handler(content_types=['document'])
def handle_pdf(message):
    if not message.document.file_name.lower().endswith('.pdf'):
        bot.reply_to(message, "يرجى إرسال ملف PDF فقط.")
        return

    file_info = bot.get_file(message.document.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    
    input_path = f"in_{message.chat.id}.pdf"
    output_path = f"Mlazma_{message.document.file_name}"
    
    with open(input_path, 'wb') as f:
        f.write(downloaded_file)

    msg = bot.reply_to(message, "⏳ جاري إعادة تنسيق وترجمة الملزمة... انتظر قليلاً.")
    
    try:
        # فتح الملف الأصلي وإنشاء ملف جديد فارغ للتنسيق
        doc = fitz.open(input_path)
        new_doc = fitz.open()
        font_path = "Amiri.ttf" # تأكد من وجود الخط في السيرفر

        for page in doc:
            new_page = new_doc.new_page() # صفحة بيضاء جديدة تماماً
            y_offset = 50 # نقطة البداية من أعلى الصفحة
            
            # 1. استخراج الصور ووضعها أولاً في الصفحة الجديدة
            images = page.get_images(full=True)
            for img in images:
                xref = img[0]
                base_image = doc.extract_image(xref)
                if base_image["width"] < 100: continue # تجاهل الصور الصغيرة جداً
                
                img_bytes = base_image["image"]
                img_rect = fitz.Rect(100, y_offset, 500, y_offset + 200) 
                new_page.insert_image(img_rect, stream=img_bytes)
                y_offset += 220 # ترك مسافة بعد الصورة
                break # نأخذ أول صورة رئيسية فقط لكل صفحة لضمان الترتيب

            # 2. استخراج النصوص وإعادة كتابتها بتنسيق (إنجليزي وتحته عربي)
            text_blocks = page.get_text("blocks")
            for block in text_blocks:
                line_text = block[4].replace('\n', ' ').strip()
                
                if len(line_text) > 2:
                    try:
                        # الترجمة
                        translated = GoogleTranslator(source='en', target='ar').translate(line_text)
                        fixed_ar = fix_arabic(translated)

                        # التحقق من نهاية الصفحة
                        if y_offset > 750:
                            new_page = new_doc.new_page()
                            y_offset = 50

                        # كتابة النص الإنجليزي (حجم 13، لون أسود)
                        new_page.insert_text((50, y_offset), line_text, fontsize=13, color=(0, 0, 0))
                        y_offset += 20
                        
                        # كتابة النص العربي تحت الإنجليزي (حجم 14، لون أحمر داكن)
                        new_page.insert_text((50, y_offset), fixed_ar, fontsize=14, fontname="f0", fontfile=font_path, color=(0.7, 0, 0))
                        y_offset += 35 # مسافة كافية قبل السطر التالي
                    except:
                        continue

        new_doc.save(output_path)
        new_doc.close()
        doc.close()

        with open(output_path, 'rb') as f:
            bot.send_document(message.chat.id, f, caption="✅ تم إعادة تنسيق الملزمة بنجاح!")
            
    except Exception as e:
        bot.reply_to(message, f"حدث خطأ: {str(e)}")
    
    # تنظيف الملفات
    if os.path.exists(input_path): os.remove(input_path)
    if os.path.exists(output_path): os.remove(output_path)

bot.polling()
