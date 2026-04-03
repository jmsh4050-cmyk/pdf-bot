import telebot
import fitz  # PyMuPDF
from deep_translator import GoogleTranslator
import os
import arabic_reshaper
from bidi.algorithm import get_display

# --- الإعدادات ---
API_TOKEN = '8723000364:AAE8SsJWHUSrFllzTFvNRRsSRJBuhBtVC3E'
bot = telebot.TeleBot(API_TOKEN)

def fix_arabic(text):
    if not text: return ""
    reshaped_text = arabic_reshaper.reshape(text)
    return get_display(reshaped_text)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "أهلاً بك في بوت إعادة تنسيق الملازم 📚\nأرسل ملف الـ PDF وسأقوم ببنائه من جديد مع الترجمة.")

@bot.message_handler(content_types=['document'])
def handle_pdf(message):
    if not message.document.file_name.lower().endswith('.pdf'):
        bot.reply_to(message, "يرجى إرسال ملف PDF فقط.")
        return

    file_info = bot.get_file(message.document.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    
    input_path = f"temp_in_{message.chat.id}.pdf"
    output_path = f"New_Format_{message.document.file_name}"
    
    with open(input_path, 'wb') as f:
        f.write(downloaded_file)

    msg = bot.reply_to(message, "⏳ جاري إعادة بناء الملزمة وترجمتها... قد يستغرق ذلك دقيقة حسب حجم الملف.")
    
    try:
        doc = fitz.open(input_path)
        new_doc = fitz.open()
        font_path = "Amiri.ttf" # ضروري جداً يكون الملف موجود

        for page in doc:
            new_page = new_doc.new_page() # صفحة بيضاء جديدة
            y_offset = 50 # البداية من الأعلى
            
            # 1. جلب الصور ووضعها في بداية الصفحة الجديدة
            images = page.get_images(full=True)
            for img in images:
                xref = img[0]
                base_image = doc.extract_image(xref)
                if base_image["width"] < 100: continue
                
                # وضع الصورة بشكل ممركز (Center)
                img_rect = fitz.Rect(100, y_offset, 500, y_offset + 220) 
                new_page.insert_image(img_rect, stream=base_image["image"])
                y_offset += 240 
                break # نأخذ صورة واحدة رئيسية لكل صفحة للحفاظ على التنسيق

            # 2. جلب النصوص وترجمتها وتنسيقها (إنجليزي وتحته عربي مباشرة)
            text_blocks = page.get_text("blocks")
            for block in text_blocks:
                line_text = block[4].replace('\n', ' ').strip()
                
                if len(line_text) > 3:
                    try:
                        # ترجمة السطر مع حماية من الأخطاء
                        translated = GoogleTranslator(source='en', target='ar').translate(line_text)
                        fixed_ar = fix_arabic(translated)

                        # إذا اقتربنا من نهاية الصفحة، نفتح صفحة جديدة
                        if y_offset > 760:
                            new_page = new_doc.new_page()
                            y_offset = 50

                        # تحديد إذا كان النص عنوان (بناءً على طول السطر)
                        is_title = len(line_text) < 30
                        f_size = 15 # حجم الخط الذي طلبته

                        # كتابة الإنجليزي (لون أحمر إذا كان عنوان، وأسود إذا نص عادي)
                        color_en = (0.8, 0, 0) if is_title else (0, 0, 0)
                        new_page.insert_text((50, y_offset), line_text, fontsize=f_size, color=color_en)
                        y_offset += 22 # مسافة للسطر العربي
                        
                        # كتابة العربي (دائماً بلون مختلف قليلاً لتمييزه)
                        new_page.insert_text((50, y_offset), fixed_ar, fontsize=f_size, fontname="f0", fontfile=font_path, color=(0.6, 0, 0))
                        y_offset += 35 # مسافة قبل الفقرة التالية
                        
                    except Exception as e:
                        print(f"Error in translation: {e}")
                        continue

        new_doc.save(output_path)
        new_doc.close()
        doc.close()

        with open(output_path, 'rb') as f:
            bot.send_document(message.chat.id, f, caption="✅ تم إعادة تنسيق وترجمة الملزمة بنجاح!")
            
    except Exception as e:
        bot.reply_to(message, f"❌ حدث خطأ تقني: {str(e)}")
    
    # حذف الملفات المؤقتة لتوفير المساحة
    if os.path.exists(input_path): os.remove(input_path)
    if os.path.exists(output_path): os.remove(output_path)

bot.polling()
